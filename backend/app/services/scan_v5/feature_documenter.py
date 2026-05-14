"""Phase 5 — Feature Documenter (R8 — AI explanation برای هر option).

برای هر UI option/setting/feature که در inventory هست، AI:
  - این گزینه دقیقاً چه می‌کند
  - کِی اضافه شد (از creation_context)
  - وضعیت فعلی (active / possibly_stale / broken / unknown)
  - dependencies + dependents
  - recommended_action (keep / remove / refactor / document)

این خروجی در UI به‌عنوان "🗺 Feature Inventory" نمایش داده می‌شود.

API:
    document_features(inventory, purpose_map, imported_by, stale_findings,
                     verify_model_id) -> Dict[item_id, doc_dict]
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MAX_OPTIONS_TO_DOCUMENT = 30
_AI_BATCH_SIZE = 8
_AI_TIMEOUT_S = 20


async def _ai_document_batch(
    batch: List[Dict[str, Any]],
    verify_model_id: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """AI call برای batch از options."""
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception:
        return {}

    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            return {}

    items_block = "\n".join(
        f"[ITEM {i}] type={it['type']} | file={it['file']} | "
        f"field={it.get('field_hint','?')} | context={it.get('context','')[:200]}"
        for i, it in enumerate(batch)
    )

    prompt = (
        "تو در حال کمک به کاربری هستی که در پروژه‌اش option/setting های "
        "زیادی دارد و فراموش کرده هرکدام چی هست. برای هر مورد زیر، "
        "یک توضیح کوتاه (۱ جمله) بنویس که کاربر بفهمد این چی هست و "
        "احتمالاً چه‌کار می‌کند. اگر اطلاعات کافی نداری، بنویس "
        "'نامشخص — بررسی manual نیاز است'.\n\n"
        f"{items_block}\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "results": [\n'
        '    {\n'
        '      "item_index": 0,\n'
        '      "what_it_does": "این گزینه ... را کنترل می‌کند",\n'
        '      "current_status": "active|possibly_stale|broken|unknown",\n'
        '      "recommended_action": "keep|remove|refactor|document"\n'
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
                max_tokens=2000,
                temperature=0.1,
                allow_fallback=True,
            ),
            timeout=_AI_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        return {}
    except Exception as e:
        logger.warning(f"feature_documenter: AI failed: {e}")
        return {}

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
    except Exception:
        return {}
    results = data.get("results", [])
    out: Dict[str, Dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("item_index"))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(batch):
            continue
        key = _item_key(batch[idx])
        out[key] = {
            "what_it_does": str(item.get("what_it_does", ""))[:300],
            "current_status": str(item.get("current_status", "unknown")).strip().lower(),
            "recommended_action": str(item.get("recommended_action", "keep")).strip().lower(),
        }
    return out


def _item_key(item: Dict[str, Any]) -> str:
    """unique key for an inventory item."""
    return f"{item.get('type','?')}:{item.get('file','?')}:{item.get('field_hint') or item.get('label') or item.get('name') or '?'}"


async def document_features(
    inventory: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    stale_findings: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    verify_model_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """ساخت feature inventory documented.

    خروجی: لیست از مدخل‌ها برای نمایش در UI.
    هر مدخل:
    {
      name, type, file, what_it_does, when_added (از creation_context),
      current_status, recommended_action, dependencies, dependents
    }
    """
    stale_findings = stale_findings or {"structural": [], "semantic": []}

    # ساخت stale lookup برای cross-reference
    stale_by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for s in stale_findings.get("structural", []) + stale_findings.get("semantic", []):
        kind = s.get("kind", "")
        stale_by_kind.setdefault(kind, []).append(s)

    # جمع‌آوری همه options/buttons/settings
    items_to_document: List[Dict[str, Any]] = []
    for opt in inventory.get("ui_options", []):
        items_to_document.append({
            "type": opt.get("type", "ui_option"),
            "file": opt.get("file"),
            "field_hint": opt.get("field_hint"),
            "context": opt.get("context", ""),
        })
    for btn in inventory.get("ui_elements", []):
        if btn.get("type") == "button" and btn.get("label"):
            items_to_document.append({
                "type": "button",
                "file": btn.get("file"),
                "field_hint": btn.get("label", ""),
                "context": btn.get("handler", ""),
            })
    items_to_document = items_to_document[:_MAX_OPTIONS_TO_DOCUMENT]

    # AI batched
    docs: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(items_to_document), _AI_BATCH_SIZE):
        batch = items_to_document[i:i + _AI_BATCH_SIZE]
        try:
            batch_docs = await _ai_document_batch(batch, verify_model_id)
            docs.update(batch_docs)
        except Exception as e:
            logger.warning(f"document batch failed: {e}")

    # ساخت output با enrichment
    out: List[Dict[str, Any]] = []
    for item in items_to_document:
        key = _item_key(item)
        doc = docs.get(key, {})
        # cross-ref با stale findings
        related_stale = []
        for s in stale_findings.get("structural", []):
            if s.get("file") == item.get("file"):
                related_stale.append(s.get("kind"))
        entry = {
            "key": key,
            "name": item.get("field_hint") or "?",
            "type": item.get("type"),
            "file": item.get("file"),
            "what_it_does": doc.get("what_it_does", "نامشخص"),
            "current_status": doc.get("current_status", "unknown"),
            "recommended_action": doc.get("recommended_action", "keep"),
            "related_stale_kinds": related_stale,
        }
        out.append(entry)
    return out
