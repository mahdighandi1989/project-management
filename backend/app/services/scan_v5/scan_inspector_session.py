"""Phase 5 — Scan Inspector Session (R14).

برای هر scan یک InspectorSession ساخته می‌شود (مشابه verify در Phase 4):
  - همه AI calls (purpose, stale, logic) → پیام در session با role="assistant"
  - همه Playwright actions → پیام با role="action" + screenshot path
  - همه screenshot ها → ذخیره روی disk + reference در session
  - runtime probe outputs → پیام با role="system"

در پایان scan:
  - session archived
  - bundle PDF با screenshots + findings + delta + logic audit
  - Telegram message + PDF attachment
  - در UI Inspector tab با badge "🔍 Scan Session"

API:
    create_scan_session(watched_id, project_name) -> session_id
    log_scan_message(session_id, role, content, ...) -> None
    archive_scan_session(session_id) -> None
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _resolve_project_id_for_watched(watched_id: str) -> str:
    """resolve watched_id به Project.id محلی تا session در tab UI ظاهر شود.

    استراتژی سه‌مرحله‌ای — دقیقاً همان منطق
    `oversight_service.resolve_project_for_task` تا scan session ها
    در همان UI tab به‌عنوان verify session ها ظاهر شوند:
      1) github_path == repo_full_name
      2) github_url LIKE %repo_full_name%
      3) extra_data.owner + extra_data.repo match (full scan روی Projects)
    در صورت شکست همه: fallback به watched_id خام.
    """
    import json as _json
    try:
        from ...core.database import SessionLocal
        from ..oversight_service import get_oversight_service
        from ...models.project import Project as _Project
        service = get_oversight_service()
        watched = service._find_watched(watched_id) if watched_id else None
        repo_full_name = (watched.repo_full_name if watched else "") or ""
        if not repo_full_name or "/" not in repo_full_name:
            logger.info(
                f"scan_inspector: no repo_full_name for watched_id={watched_id}; "
                f"falling back to raw id (UI tab won't list this session)"
            )
            return str(watched_id)
        db = SessionLocal()
        try:
            # تلاش 1: github_path
            p = db.query(_Project).filter(_Project.github_path == repo_full_name).first()
            if p:
                logger.info(
                    f"scan_inspector: resolved {repo_full_name} → "
                    f"project_id={p.id} via github_path"
                )
                return str(p.id)
            # تلاش 2: github_url contains
            p = (
                db.query(_Project)
                .filter(_Project.github_url.like(f"%{repo_full_name}%"))
                .first()
            )
            if p:
                logger.info(
                    f"scan_inspector: resolved {repo_full_name} → "
                    f"project_id={p.id} via github_url substring"
                )
                return str(p.id)
            # تلاش 3: extra_data.owner+repo (مشابه verify)
            try:
                owner, repo = repo_full_name.split("/", 1)
                for proj in db.query(_Project).all():
                    if not proj.extra_data:
                        continue
                    try:
                        ed = (
                            _json.loads(proj.extra_data)
                            if isinstance(proj.extra_data, str)
                            else proj.extra_data
                        )
                    except Exception:
                        continue
                    if (
                        isinstance(ed, dict)
                        and ed.get("owner") == owner
                        and ed.get("repo") == repo
                    ):
                        logger.info(
                            f"scan_inspector: resolved {repo_full_name} → "
                            f"project_id={proj.id} via extra_data"
                        )
                        return str(proj.id)
            except Exception as _e_ed:
                logger.debug(f"scan_inspector: extra_data scan failed: {_e_ed}")
            logger.warning(
                f"scan_inspector: no local Project matched repo='{repo_full_name}'. "
                f"Session will be saved with project_id={watched_id} but won't "
                f"appear in any /projects/[id] tab. "
                f"کاربر باید این repo را از /projects (GitHub Import) اضافه کند."
            )
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"scan_inspector: project resolve failed: {e}")
    return str(watched_id)


def create_scan_session(
    watched_id: str,
    project_name: str = "",
) -> Optional[int]:
    """ایجاد یک InspectorSession جدید برای scan.

    Returns: session_id یا None اگر DB در دسترس نباشد
    """
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorSession
    except Exception as e:
        logger.debug(f"scan_inspector: model import failed: {e}")
        return None

    # 🆕 (bug 3 fix) — resolve project_id تا session در UI tab «بازرس ویژه»
    # ظاهر شود (مشابه verify session ها)
    project_id = _resolve_project_id_for_watched(watched_id)

    db = SessionLocal()
    try:
        # 🆕 (debug) — log resolve outcome
        _was_resolved = project_id != str(watched_id)
        session = InspectorSession(
            project_id=project_id,
            status="active",
            title=f"🔍 Scan: {project_name or watched_id}",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(
            f"scan_inspector: session #{session.id} created — "
            f"project_id={project_id} (resolved={_was_resolved} from watched_id={watched_id}), "
            f"title='{session.title}'. "
            f"UI query path: /api/render/inspector/sessions/{project_id}?status=archived"
        )
        return session.id
    except Exception as e:
        logger.warning(f"scan_inspector: create_session failed: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def log_scan_message(
    session_id: Optional[int],
    role: str,
    content: str,
    action_type: Optional[str] = None,
    model_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """ثبت یک پیام در scan session.

    role: "system" | "assistant" | "action" | "user"

    🆕 (v3 resilience) — اگر extra_data بسیار بزرگ شد (>500KB JSON)،
    سعی می‌کنیم با truncate کردن content فایل‌های داخل scan_proposals
    حجم را کم کنیم. اگر باز هم insert شکست خورد، حداقل پیام بدون
    extra_data لاگ می‌شود تا کاربر بفهمد scan تمام شد.
    """
    if session_id is None:
        return
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorMessage
    except Exception:
        return

    # 🆕 (v3 resilience) — تلاش برای serialize با bounds
    def _serialize_safe(ed: Optional[Dict[str, Any]]) -> Optional[str]:
        if not ed:
            return None
        try:
            s = json.dumps(ed, ensure_ascii=False)
        except Exception as ser_e:
            logger.warning(f"scan_inspector: extra_data serialize failed: {ser_e}")
            return None
        # اگر خیلی بزرگ، بنده strong_prompt ها را truncate کن
        if len(s) > 500_000:
            try:
                trimmed = dict(ed)
                if isinstance(trimmed.get("scan_proposals"), list):
                    new_props = []
                    for p in trimmed["scan_proposals"]:
                        if isinstance(p, dict):
                            p_copy = dict(p)
                            # strong_prompt معمولاً بزرگ‌ترین بخش است
                            if isinstance(p_copy.get("strong_prompt"), str) and len(p_copy["strong_prompt"]) > 5000:
                                p_copy["strong_prompt"] = p_copy["strong_prompt"][:5000] + "\n\n[... truncated ...]"
                            if isinstance(p_copy.get("description"), str) and len(p_copy["description"]) > 3000:
                                p_copy["description"] = p_copy["description"][:3000] + "\n\n[... truncated ...]"
                            new_props.append(p_copy)
                        else:
                            new_props.append(p)
                    trimmed["scan_proposals"] = new_props
                s = json.dumps(trimmed, ensure_ascii=False)
                logger.info(f"scan_inspector: extra_data trimmed from large to {len(s)} bytes")
            except Exception:
                pass
        return s

    db = SessionLocal()
    try:
        msg = InspectorMessage(
            session_id=int(session_id),
            role=role,
            content=str(content)[:50000],
            action_type=action_type,
            model_id=model_id,
            extra_data=_serialize_safe(extra_data),
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        logger.warning(f"scan_inspector: log_message failed (will retry without extra_data): {e}")
        db.rollback()
        # 🆕 (v3 resilience) — fallback: حداقل پیام بدون extra_data لاگ شود
        # تا کاربر بفهمد scan تمام شد، حتی اگر proposals data از دست رفت
        try:
            db2 = SessionLocal()
            try:
                msg2 = InspectorMessage(
                    session_id=int(session_id),
                    role=role,
                    content=(
                        str(content)[:50000]
                        + "\n\n⚠️ [extra_data ذخیره نشد به دلیل خطای DB — proposals/scan_proposals data lost]"
                    )[:50000],
                    action_type=action_type,
                    model_id=model_id,
                    extra_data=None,
                )
                db2.add(msg2)
                db2.commit()
            finally:
                db2.close()
        except Exception as e2:
            logger.error(f"scan_inspector: fallback log also failed: {e2}")
    finally:
        db.close()


def archive_scan_session(session_id: Optional[int]) -> None:
    """بستن scan session — status=archived + closed_at."""
    if session_id is None:
        return
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorSession
    except Exception:
        return

    db = SessionLocal()
    try:
        session = db.query(InspectorSession).filter(
            InspectorSession.id == int(session_id),
        ).first()
        if session:
            session.status = "archived"
            session.closed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.debug(f"scan_inspector: archive failed: {e}")
        db.rollback()
    finally:
        db.close()


def get_scan_session_summary(session_id: Optional[int]) -> Dict[str, Any]:
    """خلاصه scan session — برای bundle و Telegram caption."""
    if session_id is None:
        return {}
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorSession
    except Exception:
        return {}

    db = SessionLocal()
    try:
        session = db.query(InspectorSession).filter(
            InspectorSession.id == int(session_id),
        ).first()
        if not session:
            return {}
        messages = session.messages or []
        by_role: Dict[str, int] = {}
        for m in messages:
            by_role[m.role] = by_role.get(m.role, 0) + 1
        return {
            "session_id": session.id,
            "title": session.title,
            "status": session.status,
            "message_count": len(messages),
            "by_role": by_role,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        }
    except Exception:
        return {}
    finally:
        db.close()
