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

    db = SessionLocal()
    try:
        session = InspectorSession(
            project_id=str(watched_id),
            status="active",
            title=f"🔍 Scan: {project_name or watched_id}",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
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
    """
    if session_id is None:
        return
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorMessage
    except Exception:
        return

    db = SessionLocal()
    try:
        msg = InspectorMessage(
            session_id=int(session_id),
            role=role,
            content=str(content)[:50000],
            action_type=action_type,
            model_id=model_id,
            extra_data=json.dumps(extra_data, ensure_ascii=False) if extra_data else None,
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        logger.debug(f"scan_inspector: log_message failed: {e}")
        db.rollback()
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
