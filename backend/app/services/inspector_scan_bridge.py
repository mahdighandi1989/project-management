"""
🆕 (inspector-scan) Bridge — وقتی intent در inspector_chat تشخیص داده شد
که scan موردی نیاز است، این ماژول scan را در background trigger می‌کند و
پیام‌های session را مدیریت می‌کند.

طراحی:
- یک scan در background دارد
- progress در همان InspectorSession لاگ می‌شود (نه به مرکز نظارت)
- در پایان، لیست proposals در یک InspectorMessage `scan_complete` لاگ می‌شود
- target_files یا commit نمی‌سازد — این مرحله بعد است (apply_all / run_proposal)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Reverse map: project_id (DB) → watched_id (in-memory) ─────────
def resolve_watched_id_from_project_id(project_id: str) -> Optional[str]:
    """نگاشت معکوس: از Project.id محلی به watched_id (in-memory oversight).

    استراتژی:
      1) Project.id → repo_full_name (از DB)
      2) repo_full_name → watched (از oversight service)
    """
    if not project_id:
        return None
    try:
        from ..core.database import SessionLocal
        from ..models.project import Project as _Project
        from .oversight_service import get_oversight_service
    except Exception as e:
        logger.debug(f"inspector_scan_bridge: import failed: {e}")
        return None

    repo_full_name: Optional[str] = None
    db = SessionLocal()
    try:
        # 1) از project_id به repo_full_name
        proj = db.query(_Project).filter(_Project.id == project_id).first()
        if proj is None:
            try:
                proj = db.query(_Project).filter(_Project.id == int(project_id)).first()
            except (ValueError, TypeError):
                proj = None
        if proj:
            # github_path معمولاً "owner/repo" است
            repo_full_name = (proj.github_path or "").strip()
            if not repo_full_name and proj.github_url:
                # fallback از URL: https://github.com/owner/repo[.git]
                url = proj.github_url.strip()
                if "github.com/" in url:
                    tail = url.split("github.com/", 1)[1]
                    tail = tail.rstrip("/").rstrip(".git")
                    if tail.count("/") >= 1:
                        repo_full_name = "/".join(tail.split("/")[:2])
            if not repo_full_name and proj.extra_data:
                try:
                    ed = json.loads(proj.extra_data) if isinstance(proj.extra_data, str) else proj.extra_data
                    if isinstance(ed, dict):
                        owner = ed.get("owner") or ""
                        repo = ed.get("repo") or ""
                        if owner and repo:
                            repo_full_name = f"{owner}/{repo}"
                except Exception:
                    pass
    finally:
        db.close()

    if not repo_full_name:
        return None

    # 2) از repo_full_name به watched_id
    try:
        svc = get_oversight_service()
        for w in svc.watched:
            if (getattr(w, "repo_full_name", "") or "").lower() == repo_full_name.lower():
                return w.id
    except Exception as e:
        logger.debug(f"inspector_scan_bridge: oversight lookup failed: {e}")
        return None
    return None


# ─── Resolve target session for chat ──────────────────────────────
def get_or_create_active_session_for_project(project_id: str) -> Optional[int]:
    """آخرین session فعال (status=active) این project را پیدا یا یک session جدید بساز.

    (audit fix I5) — race condition: دو فراخوانی هم‌زمان می‌توانند پس از
    check جداگانه هر دو insert کنند. حل: insert را در try/except و در
    صورت IntegrityError یا duplicate-found، re-query.

    Returns: session_id (int) یا None اگر DB در دسترس نباشد.
    """
    try:
        from ..core.database import SessionLocal
        from ..models.inspector_session import InspectorSession
    except Exception:
        return None

    def _find_active(db) -> Optional[int]:
        sess = (
            db.query(InspectorSession)
            .filter(
                InspectorSession.project_id == project_id,
                InspectorSession.status == "active",
            )
            .order_by(InspectorSession.created_at.desc())
            .first()
        )
        return sess.id if sess else None

    db = SessionLocal()
    try:
        existing = _find_active(db)
        if existing is not None:
            return existing
        new_sess = InspectorSession(
            project_id=project_id,
            status="active",
            title="🔍 جلسه چت بازرس",
        )
        db.add(new_sess)
        try:
            db.commit()
            db.refresh(new_sess)
            return new_sess.id
        except Exception as commit_err:
            # احتمالاً concurrent insert — re-query
            db.rollback()
            again = _find_active(db)
            if again is not None:
                return again
            logger.warning(f"create_active_session double-failure: {commit_err}")
            return None
    except Exception as e:
        logger.warning(f"get_or_create_active_session_for_project failed: {e}")
        db.rollback()
        return None
    finally:
        db.close()


# ─── Trigger scan in background ─────────────────────────────────────
# هر scan فعال در یک ditt به key = session_id ذخیره می‌شود. اگر کاربر سعی
# کند دوباره trigger کند و scan در حال اجرا داریم، 409 برمی‌گردانیم.
_ACTIVE_SCANS: Dict[int, Dict[str, Any]] = {}

# (audit fix I4) — یک قفل asyncio به ازای هر session برای جلوگیری از race
# در دو فراخوانی هم‌زمان is_scan_active + claim.
_SCAN_CLAIM_LOCK = asyncio.Lock()


def is_scan_active_for_session(session_id: int) -> bool:
    info = _ACTIVE_SCANS.get(session_id)
    return bool(info) and info.get("status") in ("queued", "running")


def get_active_scan_info(session_id: int) -> Optional[Dict[str, Any]]:
    return _ACTIVE_SCANS.get(session_id)


async def trigger_inspector_selective_scan(
    *,
    session_id: int,
    project_id: str,
    user_message: str,
    intent: "ResolvedScanIntent",  # noqa: F821 (forward ref)
    model_id: Optional[str] = None,
    model_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """نقطهٔ ورود اصلی: scan را background-trigger می‌کند.

    Returns:
        {
          "success": bool,
          "scan_id": str,
          "session_id": int,
          "watched_id": str,
          "started_message_id": Optional[int],
          "status": "queued" | "error",
          "error": Optional[str],
        }
    """
    from .scan_v5.scan_inspector_session import log_scan_message

    # (audit fix I4) — claim atomic: check + insert ضمن یک قفل تا دو
    # request هم‌زمان نتوانند هر دو scan را شروع کنند.
    scan_id = str(uuid.uuid4())[:12]
    started_at = datetime.now(timezone.utc).isoformat()

    # 2) resolve watched (می‌تواند بیرون قفل باشد)
    watched_id = resolve_watched_id_from_project_id(project_id)
    if not watched_id:
        return {
            "success": False,
            "status": "error",
            "error": f"پروژه شناسایی نشد (project_id={project_id})",
        }

    async with _SCAN_CLAIM_LOCK:
        if is_scan_active_for_session(session_id):
            return {
                "success": False,
                "status": "error",
                "error": "یک اسکن موردی دیگر در این session در حال اجراست — لطفاً منتظر بمانید.",
                "code": "scan_already_running",
                "active_scan": dict(_ACTIVE_SCANS.get(session_id) or {}),
            }
        # claim
        _ACTIVE_SCANS[session_id] = {
            "scan_id": scan_id,
            "watched_id": watched_id,
            "session_id": session_id,
            "status": "queued",
            "started_at": started_at,
        }

    # 3) لاگ پیام scan_started
    try:
        log_scan_message(
            session_id=session_id,
            role="assistant",
            content=(
                "🔍 **اسکن موردی عمیق شروع شد**\n\n"
                f"دلیل تشخیص: {intent.reason}\n"
                f"بخش‌های انتخاب‌شده: {', '.join(intent.selected_sections or []) or '—'}\n"
                f"مسیرهای سفارشی: {len(intent.custom_paths)} مسیر\n"
                f"شامل وابستگی‌ها: {'بله' if intent.include_dependencies else 'خیر'}\n"
                + (f"حالت دیباگ بصری: روشن\n" if intent.visual_debug else "")
                + "\nمنتظر بمانید — این چند دقیقه طول می‌کشد."
            ),
            action_type="scan_started",
            model_id=model_id or (model_ids[0] if model_ids else None),
            extra_data={
                "kind": "selective_scan_started",
                "scan_id": scan_id,
                "started_at": started_at,
                "intent": {
                    "reason": intent.reason,
                    "matched_keywords": intent.matched_keywords,
                    "focus_notes": intent.focus_notes[:1000],
                    "custom_paths": intent.custom_paths[:30],
                    "selected_sections": intent.selected_sections,
                    "include_dependencies": intent.include_dependencies,
                    "visual_debug": intent.visual_debug,
                    "confidence": intent.confidence,
                },
            },
        )
    except Exception as e:
        logger.warning(f"log scan_started failed: {e}")

    # (audit fix I4) — رجیستری active scan ضمن قفل بالا انجام شد، اینجا
    # duplicate نمی‌خواهیم.

    # 5) background task برای اجرای واقعی scan
    async def _bg_run():
        try:
            _ACTIVE_SCANS[session_id]["status"] = "running"
            from .oversight_deep_scan_service import run_deep_scan
            result = await run_deep_scan(
                watched_id,
                model_id=model_id,
                model_ids=model_ids,
                selected_sections=intent.selected_sections,
                custom_paths=intent.custom_paths,
                include_dependencies=intent.include_dependencies,
                focus_notes=intent.focus_notes,
                output_target=f"inspector_session:{session_id}",
                # 🆕 (v2 M2) — semantic search برای vague-intent
                semantic_keywords=(intent.semantic_keywords or None)
                                  if getattr(intent, "semantic_search_only", False) else None,
            )
            _ACTIVE_SCANS[session_id]["status"] = "completed"
            _ACTIVE_SCANS[session_id]["result"] = result
        except Exception as e:
            logger.exception(f"inspector scan bg failed: {e}")
            _ACTIVE_SCANS[session_id]["status"] = "error"
            _ACTIVE_SCANS[session_id]["error"] = str(e)[:300]
            # یک پیام error در session لاگ کن
            try:
                log_scan_message(
                    session_id=session_id,
                    role="assistant",
                    content=f"❌ اسکن موردی با خطا متوقف شد:\n```\n{str(e)[:500]}\n```",
                    action_type="scan_error",
                    extra_data={"kind": "selective_scan_error", "scan_id": scan_id, "error": str(e)[:1000]},
                )
            except Exception:
                pass
        finally:
            # نگه‌داری active record برای ۱ ساعت برای progress polling
            await asyncio.sleep(3600)
            _ACTIVE_SCANS.pop(session_id, None)

    asyncio.create_task(_bg_run())

    return {
        "success": True,
        "status": "queued",
        "scan_id": scan_id,
        "session_id": session_id,
        "watched_id": watched_id,
        "started_at": started_at,
    }


# ─── Read scan progress (UI polling) ─────────────────────────────
def read_inspector_scan_progress(session_id: int) -> Dict[str, Any]:
    """progress فعلی scan در یک session.

    اگر scan در حال اجرا است، از read_progress (مشابه deep scan) می‌خوانیم.
    اگر تمام شده، آخرین وضعیت _ACTIVE_SCANS را برمی‌گردانیم.
    """
    info = _ACTIVE_SCANS.get(session_id)
    if not info:
        return {"status": "idle", "session_id": session_id}

    response: Dict[str, Any] = {
        "scan_id": info.get("scan_id"),
        "session_id": session_id,
        "status": info.get("status", "unknown"),
        "started_at": info.get("started_at"),
        "watched_id": info.get("watched_id"),
    }

    if info.get("status") in ("queued", "running"):
        try:
            from .oversight_deep_scan_service import read_progress
            wp = read_progress(info["watched_id"])
            response.update({
                "phase": wp.get("phase"),
                "message": wp.get("message"),
                "files_total": wp.get("files_total", 0),
                "files_analyzed": wp.get("files_analyzed", 0),
                "passes_done": wp.get("passes_done", 0),
                "passes_total": wp.get("passes_total", 0),
                "scope": wp.get("scope"),
            })
        except Exception:
            pass

    if info.get("status") == "error":
        response["error"] = info.get("error")
    if info.get("status") == "completed":
        response["result"] = info.get("result")

    return response


# ─── Cancel an active scan (best effort) ──────────────────────────
def cancel_inspector_scan(session_id: int) -> bool:
    info = _ACTIVE_SCANS.get(session_id)
    if not info or info.get("status") not in ("queued", "running"):
        return False
    info["status"] = "cancelled"
    return True
