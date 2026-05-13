"""Stage 2 — AI-powered AC enricher.

این ماژول یک لیست AC (str قدیمی یا dict جدید) را می‌گیرد و با یک
فراخوانی AI، برای هر AC یک `verify_method` و در صورت لزوم
`verify_plan` ساختاریافته تولید می‌کند.

استفاده:
    from app.services.verify_runtime.ac_enricher import enrich_acs_with_verify_plans
    enriched = await enrich_acs_with_verify_plans(
        acs=task.acceptance_criteria,
        title=task.title,
        description=task.raw_idea,
        target_files=task.target_files,
        model_id="gemini-2.5-flash",
    )
    # enriched is List[Dict] with normalized structure

طراحی:
- AC هایی که قبلاً verify_method != "static" دارند یا verify_plan
  پر شده دست‌نخورده باقی می‌مانند (skip enrichment).
- بقیه به AI داده می‌شوند با یک system prompt که فقط برای classify
  استفاده می‌شود — کوتاه و سریع.
- اگر AI fail کرد یا JSON ناقص داد → AC با همان method=static
  باقی می‌ماند (graceful degrade).
- خروجی همیشه از طریق `normalize_ac_list` عبور می‌کند تا ساختار قطعی باشد.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .ac_schema import (
    AC_METHODS,
    DEFAULT_METHOD,
    normalize_ac,
    normalize_ac_list,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AI system prompt for AC enrichment
# ---------------------------------------------------------------------------

_AC_ENRICHER_SYSTEM = """You are a verification planner. For each acceptance criterion (AC) given,
you must:

1) Decide which **verify_method** is most appropriate:
   - "static" — AC مرتبط با وجود/عدم وجود کد/فایل/تابع است
     (مثل: «فایل X وجود دارد»، «import Y اضافه شد»، «class Z تعریف شد»)
   - "ui_interaction" — AC رفتار UI را توصیف می‌کند
     (مثل: «روی دکمه کلیک می‌کنم → مودال باز می‌شود»، «در صفحه نمایش داده شود»)
   - "api_response" — AC رفتار یک endpoint را توصیف می‌کند
     (مثل: «GET /api/users → 200 با field email»، «POST /login → 401 برای رمز اشتباه»)
   - "backend_test" — AC مستقیماً به یک تست pytest اشاره می‌کند
     (مثل: «test_foo pass شود»، «pytest tests/x.py سبز»)
   - "manual_only" — AC ذهنی/کیفی و قابل خودکار شدن نیست
     (مثل: «ظاهر شیک‌تر»، «UX روان‌تر»، «کاربر راضی باشد»)

2) برای method های ui_interaction/api_response/backend_test یک verify_plan
   ساختاریافته تولید کن:

   ui_interaction:
   {
     "base": "frontend",     // "frontend" یا "backend"
     "ui_steps": [   // 🆕 (Phase 3) — یک sequence ۳ تا ۸ مرحله‌ای واقعی
                     // (نه فقط navigate). راهنما در پایین.
       {"action": "navigate", "url": "/oversight"},
       {"action": "wait_for_load", "state": "networkidle"},
       {"action": "screenshot", "label": "before_interaction"},
       {"action": "click", "selector": "[data-testid='btn-x']"},
       {"action": "wait_for", "selector": "[data-testid='modal']", "timeout_ms": 3000},
       {"action": "fill", "selector": "input[name=x]", "value": "test"},
       {"action": "screenshot", "label": "after_interaction"},
       {"action": "assert_visible", "selector": "[data-testid='success']"}
     ],
     "expected_api_calls": [   // 🆕 (اختیاری) API call های مورد انتظار
       {"method": "POST", "path_contains": "/api/x"}
     ]
   }

   ⚠️ راهنمای Phase 3 برای ui_steps:
   - حداقل ۳ مرحله (navigate + wait + assert_or_screenshot)
   - برای AC با ابعاد تعاملی، حداکثر ۸ مرحله
   - selector ها را با `[data-testid='...']` ساختگی پیشنهاد بده —
     مجری باید با selector واقعی جایگزین کند (در commit message ذکر شود)
   - برای AC «نمایش بدون تعامل»، حالت کوتاه: navigate + wait + assert

   api_response:
   {
     "method": "GET",
     "path": "/api/oversight/status",
     "headers": null,
     "json_body": null,
     "expected_status": 200,
     "required_fields": ["watched_count", "tasks_count"],
     "json_contains": null
   }

   backend_test:
   {
     "test_node": "tests/test_foo.py::test_bar",
     "timeout_seconds": 60
   }

   static:
   {
     "grep_patterns": ["pattern1", "pattern2"],
     "files_hint": ["backend/app/x.py"]
   }

3) **خروجی فقط JSON** با ساختار زیر — هیچ متن دیگری بیرون JSON ننویس:
   {
     "acs": [
       {
         "index": 0,
         "verify_method": "ui_interaction",
         "verify_plan": { ... }
       },
       ...
     ]
   }

4) قواعد سخت‌گیرانه:
   - selector ها را با احتیاط بساز — اگر مطمئن نیستی selector درست است،
     از `[data-testid='...']` ساختگی استفاده کن و در commit message
     توضیح بده که مجری باید آن‌ها را با selector واقعی جایگزین کند.
   - برای api_response، path نسبی است (نه absolute URL).
   - برای backend_test، test_node فقط nodeId است (نه command کامل).
   - اگر AC از چند ادعا تشکیل شده، method اصلی را انتخاب کن.
   - اگر هیچ‌یک از method ها نمی‌خواند → "manual_only".
"""


def _build_user_message(
    acs_to_classify: List[Dict[str, Any]],
    *,
    title: str,
    description: str,
    target_files: List[str],
) -> str:
    """User-side message — context لازم برای AI."""
    parts = []
    if title:
        parts.append(f"عنوان تسک: {title}")
    if description:
        d = description[:500]
        parts.append(f"شرح: {d}")
    if target_files:
        parts.append(
            "فایل‌های هدف:\n"
            + "\n".join(f"  - {p}" for p in target_files[:10])
        )
    parts.append("\nAC ها (با index برای رفرنس در پاسخ):")
    for i, ac in enumerate(acs_to_classify):
        parts.append(f"  [{i}] {ac.get('text', '')[:300]}")
    parts.append(
        "\nخروجی فقط JSON با ساختار {\"acs\": [{\"index\": i, "
        "\"verify_method\": \"...\", \"verify_plan\": {...}}, ...]} — "
        "همان index ها را در پاسخ حفظ کن."
    )
    return "\n\n".join(parts)


def _parse_ai_response(raw: str) -> Dict[int, Dict[str, Any]]:
    """خروجی AI را به dict {index: {verify_method, verify_plan}} تبدیل می‌کند.

    در صورت پارس ناموفق، dict خالی برمی‌گرداند (graceful degrade).
    """
    if not raw or not raw.strip():
        return {}
    # سعی کن JSON اول را استخراج کنی
    try:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return {}
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        logger.debug(f"ac_enricher parse failed: {e}")
        return {}
    acs = data.get("acs")
    if not isinstance(acs, list):
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for item in acs:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        method = str(item.get("verify_method") or DEFAULT_METHOD).strip().lower()
        if method not in AC_METHODS:
            method = DEFAULT_METHOD
        plan = item.get("verify_plan")
        if not isinstance(plan, dict):
            plan = None
        out[idx] = {"verify_method": method, "verify_plan": plan}
    return out


def _ac_already_classified(ac: Dict[str, Any]) -> bool:
    """آیا این AC از قبل verify_method != static یا verify_plan پر شده دارد؟"""
    method = ac.get("verify_method") or DEFAULT_METHOD
    if method != DEFAULT_METHOD:
        return True
    plan = ac.get("verify_plan") or {}
    if isinstance(plan, dict):
        # plan با محتوای واقعی (نه فقط defaults خالی)؟
        patterns = plan.get("grep_patterns") or []
        files = plan.get("files_hint") or []
        if patterns or files:
            return True
    return False


async def enrich_acs_with_verify_plans(
    acs: Any,
    *,
    title: str = "",
    description: str = "",
    target_files: Optional[List[str]] = None,
    model_id: Optional[str] = None,
    max_acs: int = 20,
) -> List[Dict[str, Any]]:
    """لیست AC را با AI enrich می‌کند.

    Pipeline:
    1. normalize_ac_list(acs)
    2. AC هایی که قبلاً classified شده‌اند skip
    3. باقی‌مانده‌ها → یک AI call برای classify همگی همزمان
    4. merge نتایج AI با AC اصلی
    5. خروجی نهایی از طریق normalize_ac_list

    Graceful degrade:
    - اگر AI fail شد → AC ها همه با method=static باقی می‌مانند
    - اگر model_id داده نشده → از default extraction model استفاده می‌شود
    - اگر acs خالی است → list خالی برمی‌گردد

    این تابع هیچ exception ای بیرون نمی‌اندازد (مگر برنامه‌نویس).
    """
    normalized = normalize_ac_list(acs)
    if not normalized:
        return []

    target_files = target_files or []

    # AC هایی که نیاز به classify دارند
    to_classify_indices: List[int] = []
    for i, ac in enumerate(normalized):
        if not _ac_already_classified(ac):
            to_classify_indices.append(i)

    if not to_classify_indices:
        # همه classified — هیچ کاری نکن
        return normalized

    # حداکثر max_acs در یک batch
    batch = to_classify_indices[:max_acs]
    acs_in_batch = [normalized[i] for i in batch]

    # AI call
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
        if model_id is None:
            try:
                from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
                model_id = DEFAULT_EXTRACTION_MODEL_ID
            except Exception:
                pass
        if not model_id:
            logger.debug("ac_enricher: no model_id available — skipping AI enrichment")
            return normalized

        mgr = get_ai_manager()
        user_msg = _build_user_message(
            acs_in_batch,
            title=title,
            description=description,
            target_files=target_files,
        )
        messages = [
            Message(role="system", content=_AC_ENRICHER_SYSTEM),
            Message(role="user", content=user_msg),
        ]
        resp = await mgr.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=3000,
            temperature=0.1,
            allow_fallback=True,
        )
        raw = (resp.content or "").strip()
    except Exception as e:
        logger.warning(f"ac_enricher AI call failed: {e} — همه AC با method=static باقی می‌مانند")
        return normalized

    parsed = _parse_ai_response(raw)
    if not parsed:
        logger.debug("ac_enricher: AI پاسخ JSON قابل پارس نداد — graceful degrade")
        return normalized

    # merge: index در batch → index در normalized
    for batch_idx, orig_idx in enumerate(batch):
        if batch_idx not in parsed:
            continue
        info = parsed[batch_idx]
        method = info["verify_method"]
        plan = info["verify_plan"]
        normalized[orig_idx]["verify_method"] = method
        if plan is not None:
            normalized[orig_idx]["verify_plan"] = plan

    # یک بار دیگر normalize تا اطمینان از valid بودن plan ها
    return normalize_ac_list(normalized)
