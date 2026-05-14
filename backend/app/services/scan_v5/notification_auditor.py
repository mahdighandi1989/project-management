"""Phase 5 — Notification Auditor (R12).

برای هر `notify_event(...)` call در کد:
  - caption کامل/ناقص است؟
  - silent/sound مناسب است؟ (critical=sound, routine=silent)
  - attachments صحیح؟ (task creation → prompt.md, verify → bundle.pdf,
    scan → scan-bundle.pdf)
  - stale notifications (event type که دیگر کد آن وجود ندارد)
  - missing notifications (event critical که notification ندارد)

API:
    audit_notifications(inventory, purpose_map, file_contents,
                       verify_model_id) -> Dict
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_AI_TIMEOUT_S = 25
_KNOWN_EVENT_TYPES = {
    "task_created", "task_done", "task_failed",
    "verify_completed", "verify_done", "verify_failed",
    "scan_started", "scan_completed", "scan_failed",
    "auto_apply_done", "auto_apply_failed",
    "deploy_done", "deploy_failed",
    "backfill_completed", "manual_apply_request",
}

# Events که "critical" هستند (باید با صدا notify شوند)
_CRITICAL_EVENT_TYPES = {
    "task_failed", "verify_failed", "scan_failed",
    "auto_apply_failed", "deploy_failed",
    "manual_apply_request",
}


def _structural_audit(
    notification_inventory: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """audit ساختاری روی notification calls."""
    issues: List[Dict[str, Any]] = []
    seen_event_types: Set[str] = set()

    for n in notification_inventory:
        event_type = n.get("event_type")
        silent = n.get("silent_default")
        file_path = n.get("file")

        if event_type:
            seen_event_types.add(event_type)

        # Issue 1: silent flag undefined
        if silent is None:
            issues.append({
                "kind": "silent_flag_undefined",
                "file": file_path,
                "line": n.get("line"),
                "event_type": event_type or "?",
                "severity": "low",
                "reason": (
                    "silent flag صریحاً ست نشده — پیش‌فرض ممکن است "
                    "برای event مناسب نباشد"
                ),
                "suggestion": (
                    f"silent=True برای event های routine، silent=False "
                    f"برای critical (مثل {sorted(_CRITICAL_EVENT_TYPES)[:3]})"
                ),
            })

        # Issue 2: event_type missing
        if not event_type:
            issues.append({
                "kind": "event_type_missing",
                "file": file_path,
                "line": n.get("line"),
                "severity": "medium",
                "reason": "notification call بدون event_type صریح — "
                          "audit و filtering مشکل می‌شود",
                "suggestion": "event=\"task_done\" یا مشابه اضافه کن",
            })

        # Issue 3: silent mismatched with criticality
        if silent == "True" and event_type in _CRITICAL_EVENT_TYPES:
            issues.append({
                "kind": "silent_critical_mismatch",
                "file": file_path,
                "line": n.get("line"),
                "event_type": event_type,
                "severity": "high",
                "reason": (
                    f"event '{event_type}' critical است ولی silent=True — "
                    "کاربر notification را نخواهد دید"
                ),
                "suggestion": "silent=False برای این event",
            })

        # Issue 4: silent=False برای event های routine
        if silent == "False" and event_type and event_type not in _CRITICAL_EVENT_TYPES:
            if event_type in {"task_created", "scan_completed", "auto_apply_done"}:
                issues.append({
                    "kind": "sound_routine_mismatch",
                    "file": file_path,
                    "line": n.get("line"),
                    "event_type": event_type,
                    "severity": "low",
                    "reason": (
                        f"event '{event_type}' routine است ولی silent=False — "
                        "ممکن است notification noise شود"
                    ),
                    "suggestion": "silent=True برای کاهش noise",
                })

    # Issue 5: missing critical events
    for crit_event in _CRITICAL_EVENT_TYPES:
        if crit_event not in seen_event_types and crit_event in (
            "task_failed", "scan_failed", "verify_failed",
        ):
            issues.append({
                "kind": "missing_critical_notification",
                "event_type": crit_event,
                "severity": "high",
                "reason": (
                    f"event critical '{crit_event}' هیچ notification ندارد"
                ),
                "suggestion": (
                    f"اضافه کردن notify_event برای '{crit_event}' "
                    f"در failure handler مربوطه"
                ),
            })

    return issues


async def _ai_audit_notification_templates(
    notification_inventory: List[Dict[str, Any]],
    verify_model_id: Optional[str],
) -> List[Dict[str, Any]]:
    """AI تحلیل caption templates و suggested improvements."""
    if not notification_inventory:
        return []
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception:
        return []
    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            return []

    # نمونه ۱۰ caption مختلف برای audit
    sample = notification_inventory[:10]
    samples_block = "\n".join(
        f"[{i}] event={n.get('event_type','?')} silent={n.get('silent_default')} "
        f"file={n.get('file','?')}:{n.get('line','?')}\n"
        f"   context: {n.get('context_snippet','')[:200]}"
        for i, n in enumerate(sample)
    )

    prompt = (
        "تو یک UX engineer هستی. این notification call ها را audit کن:\n\n"
        f"{samples_block}\n\n"
        "موارد بررسی:\n"
        "1. caption کامل است؟ (title، context، action link، attachments)\n"
        "2. silent/sound مناسب criticality event؟\n"
        "3. attachments صحیح؟ (task → prompt.md، scan → bundle.pdf)\n"
        "4. caption تکراری یا یکنواخت بین event types؟\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "issues": [\n'
        '    {"sample_index": int, "kind": "caption_incomplete|attachment_wrong|template_duplicate|...", '
        '"reason": "...", "suggested_template": "...", "severity": "high|medium|low"},\n'
        '    ...\n'
        '  ]\n'
        "}"
    )
    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=2000,
                temperature=0.1,
                allow_fallback=True,
            ),
            timeout=_AI_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        s = raw.find("{"); e = raw.rfind("}")
        if s == -1 or e <= s:
            return []
        data = json.loads(raw[s:e + 1])
        out: List[Dict[str, Any]] = []
        for i in (data.get("issues") or []):
            if isinstance(i, dict):
                idx = i.get("sample_index", 0)
                src = sample[idx] if 0 <= int(idx) < len(sample) else {}
                out.append({
                    "kind": str(i.get("kind", "template_issue"))[:50],
                    "file": src.get("file"),
                    "line": src.get("line"),
                    "event_type": src.get("event_type"),
                    "severity": str(i.get("severity", "medium")).lower(),
                    "reason": str(i.get("reason", ""))[:400],
                    "suggested_template": str(i.get("suggested_template", ""))[:500],
                    "_source": "ai",
                })
        return out
    except Exception as e:
        logger.warning(f"AI notification audit failed: {e}")
        return []


async def audit_notifications(
    inventory: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """audit کامل سیستم notification.

    Returns:
        {
            "structural_issues": [...],
            "ai_template_issues": [...],
            "summary": {
                "total_calls": int,
                "missing_silent_flag": int,
                "missing_event_type": int,
                "critical_silent_mismatch": int,
                "missing_critical_events": int,
            }
        }
    """
    notif_inv = inventory.get("notification_calls", [])
    structural = _structural_audit(notif_inv)
    ai_issues: List[Dict[str, Any]] = []
    try:
        ai_issues = await _ai_audit_notification_templates(notif_inv, verify_model_id)
    except Exception as e:
        logger.warning(f"AI notification template audit failed: {e}")

    summary = {
        "total_calls": len(notif_inv),
        "missing_silent_flag": sum(1 for i in structural if i["kind"] == "silent_flag_undefined"),
        "missing_event_type": sum(1 for i in structural if i["kind"] == "event_type_missing"),
        "critical_silent_mismatch": sum(1 for i in structural if i["kind"] == "silent_critical_mismatch"),
        "missing_critical_events": sum(1 for i in structural if i["kind"] == "missing_critical_notification"),
        "total_issues": len(structural) + len(ai_issues),
    }
    return {
        "structural_issues": structural,
        "ai_template_issues": ai_issues,
        "summary": summary,
    }
