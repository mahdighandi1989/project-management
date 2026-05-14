"""Phase 5 — Pipeline Coherence Analyzer (R10, R11).

تشخیص chains از componentهای همکار و بررسی coherence منطقی آن‌ها:
  - Data pipeline: schema در هر مرحله سازگار؟
  - AI/LLM chain: prompt ↔ model ↔ parser سازگار؟
  - Business logic (R11 مثال trade): signal ↔ risk ↔ executor
  - Auth/Permission: همه mutation paths از permission می‌گذرند؟
  - Feedback loop: outcome به config/model برمی‌گردد؟
  - Notification chain (R12): event → notify → caption → silent → delivery

API:
    detect_pipelines(purpose_map, inventory) -> List[Pipeline]
    analyze_coherence(pipelines, purpose_map, file_contents, verify_model_id)
        -> List[CoherenceIssue]
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_AI_TIMEOUT_S = 30
_MAX_PIPELINES_TO_ANALYZE = 5


# Heuristic pipeline detection — pattern → category
_PIPELINE_KEYWORDS = {
    "ai_llm": ["prompt", "ai_manager", "ai_client", "parser", "vision", "generate"],
    "data": ["fetch", "transform", "store", "ingest", "etl", "stream"],
    "business": ["signal", "trade", "order", "strategy", "executor", "risk"],
    "auth": ["auth", "permission", "token", "credential", "login", "session"],
    "feedback": ["outcome", "metric", "feedback", "learn", "improve"],
    "notification": ["notify", "telegram", "compose", "send", "alert"],
}


def detect_pipelines(
    purpose_map: Dict[str, Dict[str, Any]],
    inventory: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """تشخیص pipelines (chains of cooperating components) — heuristic."""
    pipelines: Dict[str, Dict[str, Any]] = {}

    for path, purpose in purpose_map.items():
        purpose_text = (purpose.get("stated_purpose") or "").lower()
        responsibility = (purpose.get("main_responsibility") or "").lower()
        combined = purpose_text + " " + responsibility + " " + path.lower()

        # match against categories
        for category, keywords in _PIPELINE_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                pipelines.setdefault(category, {
                    "category": category,
                    "components": [],
                    "interactions": set(),
                })
                pipelines[category]["components"].append({
                    "path": path,
                    "responsibility": responsibility,
                    "interacts_with": purpose.get("interacting_with", []),
                })
                # build interactions
                for partner in purpose.get("interacting_with", []):
                    pipelines[category]["interactions"].add(partner)

    # convert to list + serialize sets
    out: List[Dict[str, Any]] = []
    for cat, p in pipelines.items():
        if len(p["components"]) < 2:
            continue  # یک‌مولفه‌ای — pipeline نیست
        out.append({
            "category": cat,
            "components": p["components"][:8],
            "interactions": sorted(list(p["interactions"]))[:10],
            "component_count": len(p["components"]),
        })
    # sort by component count desc
    out.sort(key=lambda x: -x["component_count"])
    return out[:_MAX_PIPELINES_TO_ANALYZE]


async def _ai_analyze_pipeline(
    pipeline: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
    verify_model_id: Optional[str],
) -> List[Dict[str, Any]]:
    """AI تحلیل coherence یک pipeline."""
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

    cat = pipeline["category"]
    comps = pipeline["components"]
    comps_block = "\n".join(
        f"- {c['path']}\n"
        f"  responsibility: {c.get('responsibility', '?')}\n"
        f"  purpose: {(purpose_map.get(c['path'], {}).get('stated_purpose') or '?')[:200]}\n"
        f"  expected_inputs: {purpose_map.get(c['path'], {}).get('expected_inputs', [])}\n"
        f"  expected_outputs: {purpose_map.get(c['path'], {}).get('expected_outputs', [])}\n"
        f"  interacts_with: {c.get('interacts_with', [])}\n"
        for c in comps[:6]
    )

    coherence_rules = {
        "ai_llm": "آیا prompt format با AI model و output parser سازگار است؟ "
                  "آیا validation روی AI response هست؟ آیا hallucination guards فعال‌اند؟",
        "data": "آیا schema در هر مرحله سازگار است؟ آیا empty result handle می‌شود؟",
        "business": "آیا signal با risk model، position با account size، "
                    "stop-loss با timeframe سازگار است؟",
        "auth": "آیا همه‌ی mutation paths از permission می‌گذرند؟ "
                "آیا permission info leak نمی‌شود؟",
        "feedback": "آیا outcome ها به config یا model برمی‌گردند (learning loop)؟",
        "notification": "آیا event → notify_event → caption → silent → delivery "
                        "همگی سازگار؟ silent برای critical events است؟",
    }
    rule = coherence_rules.get(cat, "آیا اجزای این pipeline منطقاً همسو هستند؟")

    prompt = (
        f"تو یک Code Reviewer هستی. این یک **{cat} pipeline** است.\n\n"
        f"📋 components:\n{comps_block}\n\n"
        f"⚠️ بررسی coherence:\n{rule}\n\n"
        "هر inconsistency منطقی را شناسایی کن و خروجی JSON بده.\n"
        "هر issue باید:\n"
        "- title کوتاه\n"
        "- description (چرا inconsistent است)\n"
        "- impact (چه می‌شود اگر رفع نشود)\n"
        "- suggested_fix (مختصر)\n"
        "- priority: critical|high|medium|low\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "issues": [\n'
        '    {"title": "...", "description": "...", "impact": "...", '
        '"suggested_fix": "...", "priority": "..."},\n'
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
        issues = data.get("issues") or []
        out: List[Dict[str, Any]] = []
        for i in issues:
            if isinstance(i, dict):
                out.append({
                    "pipeline_category": cat,
                    "title": str(i.get("title", ""))[:200],
                    "description": str(i.get("description", ""))[:500],
                    "impact": str(i.get("impact", ""))[:300],
                    "suggested_fix": str(i.get("suggested_fix", ""))[:400],
                    "priority": str(i.get("priority", "medium")).lower(),
                })
        return out
    except Exception as e:
        logger.warning(f"coherence AI failed for {cat}: {e}")
        return []


async def analyze_coherence(
    purpose_map: Dict[str, Dict[str, Any]],
    inventory: Dict[str, Any],
    file_contents: Dict[str, str],
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """تحلیل coherence همه pipelines."""
    pipelines = detect_pipelines(purpose_map, inventory)
    all_issues: List[Dict[str, Any]] = []
    for p in pipelines:
        try:
            issues = await _ai_analyze_pipeline(p, purpose_map, file_contents, verify_model_id)
            all_issues.extend(issues)
        except Exception as e:
            logger.warning(f"pipeline {p.get('category')} analysis failed: {e}")
    return {
        "pipelines_detected": [
            {"category": p["category"], "component_count": p["component_count"]}
            for p in pipelines
        ],
        "issues": all_issues,
    }
