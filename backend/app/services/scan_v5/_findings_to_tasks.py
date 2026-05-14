"""Phase 5 — Findings → Standard Tasks Converter.

این ماژول crucial integration گم‌شده را پر می‌کند:
Phase 5 findings (stale, anti-pattern, coherence, effectiveness,
notification audit, change-impact) → standard finding dict که در
run_deep_scan به task تبدیل می‌شود.

بدون این، Phase 5 یافته‌ها تولید می‌کرد ولی **هرگز task ایجاد نمی‌شد**.

API:
    phase5_findings_to_standard(stale, anti_patterns, ...) -> List[Dict]
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _priority_for_severity(severity: Optional[str], default: str = "medium") -> str:
    s = (severity or "").strip().lower()
    if s in ("critical", "high", "medium", "low"):
        return s
    if s == "error":
        return "high"
    if s in ("warning", "warn"):
        return "medium"
    if s == "info":
        return "low"
    return default


def _stale_to_finding(stale_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = stale_item.get("kind", "")
    detector = stale_item.get("_detector", "")
    if not kind:
        return None
    titles = {
        "dead_ui_button": f"دکمه‌ی UI بدون handler: {str(stale_item.get('label', '?'))[:60]}",
        "dead_frontend_route": f"route فرانت‌اند بلااستفاده: {stale_item.get('route', '?')}",
        "dead_backend_endpoint": f"endpoint بک‌اند بلااستفاده: {stale_item.get('method', '?')} {str(stale_item.get('path', '?'))[:60]}",
        "unused_file": f"فایل بدون import مرجع: {(stale_item.get('file') or '?').rsplit('/', 1)[-1]}",
        "unused_dataclass_field": f"فیلد بلااستفاده: {stale_item.get('class', '?')}.{stale_item.get('field', '?')}",
        "unused_env_var": f"env var بلااستفاده: {stale_item.get('name', '?')}",
        "stale_dependency": f"dependency بلااستفاده: {stale_item.get('name', '?')} ({stale_item.get('lang', '?')})",
        "hidden_purpose": f"فایل با هدف مبهم: {(stale_item.get('file') or '?').rsplit('/', 1)[-1]}",
        "forgotten_option": f"UI option با نام مبهم: {stale_item.get('field_hint', '?')}",
    }
    title = titles.get(kind, f"stale item: {kind}")
    target_files: List[str] = []
    if stale_item.get("file"):
        target_files.append(stale_item["file"])
    if kind == "hidden_purpose":
        task_type, priority = "audit", "medium"
    elif kind in ("dead_ui_button", "dead_frontend_route", "unused_file",
                  "unused_env_var", "stale_dependency"):
        task_type, priority = "cleanup", "medium"
    else:
        task_type, priority = "audit", "low"
    description = (
        f"{stale_item.get('reason', '')}\n\n"
        f"🎯 پیشنهاد:\n"
        f"یا این مورد را حذف کن (اگر منسوخ است)، یا با docstring/comment "
        f"توضیح بده چرا نگه داشته شده، یا اگر هنوز معتبر است ولی ناقص "
        f"است، ارتقاء بده."
    )
    return {
        "type": task_type,
        "priority": priority,
        "title": title,
        "description": description,
        "target_files": target_files,
        "target_locations": [{"path": p, "lines": ""} for p in target_files],
        "_pass": "phase5_stale",
        "_source": f"scan_v5/stale_detector:{detector}",
        "_stale_kind": kind,
    }


def _anti_pattern_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = item.get("kind", "anti_pattern")
    file_ = item.get("file") or ""
    if not kind:
        return None
    line = item.get("line") or item.get("line_hint")
    titles = {
        "magic_threshold": "Magic threshold — مقدار عددی بدون توضیح",
        "silent_failure": "Silent failure — except: pass در مسیر crucial",
        "unused_data_write": f"داده‌ی بی‌مصرف: {item.get('attribute', '?')}",
        "conflicting_default": f"تضاد default برای فیلد '{item.get('field', '?')}'",
    }
    title = titles.get(kind, f"Anti-pattern: {kind}")
    description = (
        f"{item.get('reason') or item.get('description', '')}\n\n"
        f"📁 file: {file_}{f' (line {line})' if line else ''}\n\n"
        f"🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند. "
        f"بازنگری کن و اگر intentional است، با کامنت توضیح بده."
    )
    target_files = [file_] if file_ else []
    priority = _priority_for_severity(item.get("priority") or item.get("severity"), "medium")
    return {
        "type": "refactor" if kind == "magic_threshold" else "bug_fix",
        "priority": priority,
        "title": title,
        "description": description,
        "target_files": target_files,
        "target_locations": ([{"path": file_, "lines": str(line) if line else ""}] if file_ else []),
        "_pass": "phase5_anti_pattern",
        "_source": f"scan_v5/anti_pattern:{item.get('_source', '?')}",
    }


def _coherence_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = item.get("title") or ""
    if not title:
        return None
    cat = item.get("pipeline_category", "?")
    description = (
        f"📍 pipeline: {cat}\n\n"
        f"{item.get('description', '')}\n\n"
        f"🎯 پیامد: {item.get('impact', '')}\n\n"
        f"🛠 پیشنهاد رفع: {item.get('suggested_fix', '')}"
    )
    priority = _priority_for_severity(item.get("priority"), "medium")
    return {
        "type": "logic_audit",
        "priority": priority,
        "title": f"[منطق] {title[:120]}",
        "description": description,
        "target_files": [],
        "target_locations": [],
        "_pass": "phase5_coherence",
        "_source": "scan_v5/coherence_analyzer",
    }


def _effectiveness_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = item.get("title") or ""
    if not title:
        return None
    description = (
        f"🎯 هدف مطلوب (outcome): {item.get('outcome_target', '')}\n\n"
        f"📊 وضعیت فعلی: {item.get('current_state', '')}\n\n"
        f"🛠 اقدام پیشنهادی: {item.get('suggested_action', '')}\n\n"
        f"⚙️ نوع: AC outcome-oriented — verify باید outcome را اندازه بگیرد، نه فقط existence."
    )
    priority = _priority_for_severity(item.get("priority"), "high")
    return {
        "type": "logic_audit",
        "priority": priority,
        "title": f"[Effectiveness] {title[:120]}",
        "description": description,
        "target_files": [],
        "target_locations": [],
        "_pass": "phase5_effectiveness",
        "_source": "scan_v5/outcome_analyzer",
    }


def _notification_issue_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = item.get("kind", "")
    file_ = item.get("file") or ""
    if not kind:
        return None
    event = item.get("event_type") or ""
    titles = {
        "silent_flag_undefined": f"notification بدون silent flag صریح — {event or 'event ناشناخته'}",
        "event_type_missing": f"notification بدون event_type صریح در {file_.rsplit('/', 1)[-1]}",
        "silent_critical_mismatch": f"event critical '{event}' با silent=True (کاربر نمی‌بیند)",
        "sound_routine_mismatch": f"event routine '{event}' با silent=False (noise)",
        "missing_critical_notification": f"event critical '{event}' هیچ notification ندارد",
    }
    title = titles.get(kind, f"audit notification: {kind}")
    description = (
        f"{item.get('reason', '')}\n\n"
        f"🛠 پیشنهاد: {item.get('suggestion') or item.get('suggested_template', '')}"
    )
    priority = _priority_for_severity(item.get("severity"), "medium")
    return {
        "type": "notification_audit",
        "priority": priority,
        "title": title,
        "description": description,
        "target_files": [file_] if file_ else [],
        "target_locations": ([{"path": file_, "lines": str(item.get("line", ""))}] if file_ else []),
        "_pass": "phase5_notification_audit",
        "_source": "scan_v5/notification_auditor",
    }


def _change_impact_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if item.get("recommended_action") == "no_action":
        if item.get("risk") not in ("high", "medium"):
            return None
    changed = item.get("changed_file", "?")
    dependent = item.get("dependent_file", "?")
    title = (
        f"🔄 {(dependent or '?').rsplit('/', 1)[-1]} نیازمند بررسی به‌خاطر "
        f"تغییر در {(changed or '?').rsplit('/', 1)[-1]}"
    )
    description = (
        f"📂 changed: {changed}\n"
        f"📂 dependent: {dependent}\n"
        f"🔥 risk: {item.get('risk', '?')}\n"
        f"📝 reason: {item.get('reason', '')}\n\n"
        f"🛠 action: {item.get('recommended_action', '?')}"
    )
    priority_map = {"high": "high", "medium": "medium", "low": "low"}
    priority = priority_map.get(str(item.get("risk", "")).lower(), "medium")
    return {
        "type": "dependency_update",
        "priority": priority,
        "title": title,
        "description": description,
        "target_files": [dependent] if dependent and dependent != "?" else [],
        "target_locations": (
            [{"path": dependent, "lines": ""}] if dependent and dependent != "?" else []
        ),
        "_pass": "phase5_change_impact",
        "_source": "scan_v5/dependency_analyzer",
    }


def phase5_findings_to_standard(
    stale: Optional[Dict[str, Any]] = None,
    anti_patterns: Optional[List[Dict[str, Any]]] = None,
    coherence_issues: Optional[List[Dict[str, Any]]] = None,
    effectiveness_issues: Optional[List[Dict[str, Any]]] = None,
    notification_audit: Optional[Dict[str, Any]] = None,
    change_impact: Optional[List[Dict[str, Any]]] = None,
    delta: Optional[Dict[str, Any]] = None,
    inventory: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """تبدیل تمام Phase 5 findings به standard findings."""
    out: List[Dict[str, Any]] = []
    if stale:
        for s in (stale.get("structural") or []):
            try:
                f = _stale_to_finding(s)
                if f:
                    out.append(f)
            except Exception as e:
                logger.debug(f"stale → finding failed: {e}")
        for s in (stale.get("semantic") or []):
            try:
                f = _stale_to_finding(s)
                if f:
                    out.append(f)
            except Exception:
                pass
    for ap in (anti_patterns or []):
        try:
            f = _anti_pattern_to_finding(ap)
            if f:
                out.append(f)
        except Exception:
            pass
    for c in (coherence_issues or []):
        try:
            f = _coherence_to_finding(c)
            if f:
                out.append(f)
        except Exception:
            pass
    for e in (effectiveness_issues or []):
        try:
            f = _effectiveness_to_finding(e)
            if f:
                out.append(f)
        except Exception:
            pass
    if notification_audit:
        for n in (notification_audit.get("structural_issues") or []):
            try:
                f = _notification_issue_to_finding(n)
                if f:
                    out.append(f)
            except Exception:
                pass
        for n in (notification_audit.get("ai_template_issues") or []):
            try:
                f = _notification_issue_to_finding(n)
                if f:
                    out.append(f)
            except Exception:
                pass
    for ci in (change_impact or []):
        try:
            f = _change_impact_to_finding(ci)
            if f:
                out.append(f)
        except Exception:
            pass
    return out
