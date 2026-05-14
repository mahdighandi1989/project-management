"""Phase 5 — Outcome Data Collector + Effectiveness Audit (R11).

برای هر پروژه، outcome data (نتایج عملی) را جمع‌آوری می‌کند:
  - Render logs filtered by event types
  - DB tables outcome-naming (مثل trade_history, conversation_logs)
  - file artifacts (در پوشه‌ی outputs/)

سپس AI evaluate می‌کند:
  - آیا outcome با stated_purpose می‌خواند؟
  - effectiveness score (LOW/MEDIUM/HIGH)
  - مثال trade: اگر purpose="earn profit" و win-rate=30% → LOW

API:
    collect_outcome_data(inventory, purpose_map, render_logs) -> outcome_dict
    audit_effectiveness(outcome_data, purpose_map, verify_model_id) -> List[Dict]
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_AI_TIMEOUT_S = 25


def _infer_project_type(
    inventory: Dict[str, Any], purpose_map: Dict[str, Dict[str, Any]],
) -> str:
    """تشخیص نوع پروژه: trading / chat / web / scheduler / notification / general."""
    all_text = " ".join(
        (p.get("stated_purpose") or "")
        for p in purpose_map.values()
    ).lower()
    file_names = " ".join(inventory.get("files", [])).lower()
    combined = all_text + " " + file_names
    if any(k in combined for k in ("trade", "binance", "kraken", "signal", "position", "p&l", "strategy")):
        return "trading"
    if any(k in combined for k in ("chat", "conversation", "message", "llm", "openai", "claude", "gpt")):
        return "chat_ai"
    if any(k in combined for k in ("scheduler", "cron", "apscheduler", "background task")):
        return "scheduler"
    if "notification" in combined or "telegram" in combined:
        return "notification"
    if any(k in combined for k in ("fastapi", "router", "endpoint", "rest")):
        return "web_service"
    return "general"


def collect_outcome_data(
    inventory: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    render_logs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """جمع‌آوری outcome data از sources در دسترس."""
    project_type = _infer_project_type(inventory, purpose_map)
    out: Dict[str, Any] = {
        "project_type": project_type,
        "error_rate_30d": None,
        "warn_count_30d": None,
        "info_count_30d": None,
        "sample_errors": [],
        "_source": "render_logs" if render_logs else "none",
    }
    if not render_logs:
        return out

    # شمارش error/warn/info
    error_count = 0
    warn_count = 0
    info_count = 0
    samples_err: List[str] = []
    for log in render_logs[:1000]:
        level = (log.get("level") or "").lower()
        msg = (log.get("message") or "")[:200]
        if level == "error":
            error_count += 1
            if len(samples_err) < 5:
                samples_err.append(msg)
        elif level == "warn":
            warn_count += 1
        elif level == "info":
            info_count += 1
    total = error_count + warn_count + info_count
    out["error_rate_30d"] = round(error_count / total, 3) if total else None
    out["warn_count_30d"] = warn_count
    out["info_count_30d"] = info_count
    out["sample_errors"] = samples_err

    # برای پروژه trade، تلاش کن signals/trades را پیدا کنی
    if project_type == "trading":
        trade_keywords = ("trade", "signal", "position", "p&l", "profit", "loss")
        trade_logs = [
            l for l in render_logs
            if any(k in (l.get("message") or "").lower() for k in trade_keywords)
        ][:50]
        out["trade_log_sample"] = [l.get("message", "")[:200] for l in trade_logs]

    return out


async def audit_effectiveness(
    outcome_data: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    verify_model_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """AI تحلیل کند: آیا outcome با purpose می‌خواند؟

    خروجی: لیست از effectiveness issues که می‌توانند task شوند.
    """
    if not outcome_data or outcome_data.get("_source") == "none":
        return []

    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
        if not verify_model_id:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
    except Exception:
        return []

    if not verify_model_id:
        return []

    project_type = outcome_data.get("project_type", "general")
    # خلاصه‌ی main purposes (top 5 important)
    top_purposes = sorted(
        purpose_map.items(),
        key=lambda x: -x[1].get("importance_score", 0),
    )[:5]
    purposes_block = "\n".join(
        f"- {path}: {(p.get('stated_purpose') or '?')[:200]}"
        for path, p in top_purposes
    )

    outcome_block = json.dumps(
        {k: v for k, v in outcome_data.items() if not k.startswith("_")},
        ensure_ascii=False, indent=2,
    )[:3000]

    prompt = (
        f"تو یک Engineering Manager هستی. این یک پروژه‌ی **{project_type}** است.\n\n"
        f"📋 هدف اصلی components:\n{purposes_block}\n\n"
        f"📊 outcome data (نتایج عملی ۳۰ روز اخیر):\n```\n{outcome_block}\n```\n\n"
        "آیا outcome data نشان می‌دهد سیستم به هدف اصلی خود رسیده؟\n"
        "- error_rate بالا (>5%) = LOW effectiveness\n"
        "- error_rate متوسط (1-5%) = MEDIUM\n"
        "- error_rate کم (<1%) = HIGH (در صورت purpose-matching)\n"
        "- برای trading: trades ضررده > 60% = LOW حتی اگر error_rate کم\n\n"
        "اگر effectiveness LOW یا MEDIUM، چند issue مشخص گزارش کن.\n"
        "هر issue باید **outcome-oriented** باشد:\n"
        "  ❌ «این کد را fix کن»\n"
        "  ✅ «بعد از این تغییر، X% trades باید سودده باشد»\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "overall_effectiveness": "low|medium|high",\n'
        '  "issues": [\n'
        '    {\n'
        '      "title": "...",\n'
        '      "outcome_target": "...",  # رفتار مطلوب\n'
        '      "current_state": "...",\n'
        '      "priority": "critical|high|medium|low",\n'
        '      "suggested_action": "..."\n'
        '    }, ...\n'
        '  ]\n'
        "}"
    )
    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=2500,
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
        issues = data.get("issues") or []
        out: List[Dict[str, Any]] = []
        for i in issues:
            if isinstance(i, dict):
                out.append({
                    "title": str(i.get("title", ""))[:200],
                    "outcome_target": str(i.get("outcome_target", ""))[:400],
                    "current_state": str(i.get("current_state", ""))[:400],
                    "priority": str(i.get("priority", "medium")).lower(),
                    "suggested_action": str(i.get("suggested_action", ""))[:400],
                    "overall_effectiveness": data.get("overall_effectiveness", "unknown"),
                })
        return out
    except Exception as e:
        logger.warning(f"effectiveness audit failed: {e}")
        return []
