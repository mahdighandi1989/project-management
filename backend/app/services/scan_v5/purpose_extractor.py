"""Phase 5 — Purpose Extractor (R10 — منطق و هدف).

برای هر file/module/feature/option استخراج می‌کند:
  - stated_purpose: چه کاری *قرار است* بکند (از doc/comment/test/raw_idea)
  - expected_inputs/outputs
  - interacting_with: همکارها (forward dependency منطقی)
  - creation_context: کِی، چرا، توسط کدام task ایجاد شد (R8)
  - current_usage: آیا هنوز استفاده می‌شود

این ماژول از AI استفاده می‌کند ولی **fail-soft** است: اگر AI در دسترس
نباشد، purpose خالی برمی‌گردد و scan بقیه فاز ها را ادامه می‌دهد.

API اصلی:
    extract_purposes(inventory, file_contents, task_history, repo_full_name,
                     token, verify_model_id) -> Dict[item_id, purpose_dict]
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# محدودیت‌ها
_MAX_FILES_TO_PURPOSE = 30  # کند است (AI call per file)
_MAX_CONTENT_FOR_AI = 6000  # هر فایل
_AI_TIMEOUT_S = 25
_AI_BATCH_SIZE = 5  # AI روی N فایل در یک call


def _file_importance_score(
    path: str,
    file_contents: Dict[str, str],
    reverse_imports: Dict[str, List[str]],
) -> int:
    """امتیاز اهمیت برای انتخاب کدام فایل‌ها purpose بگیرند."""
    score = 0
    # فایل‌های python که reverse-import دارند
    if path.endswith(".py"):
        score += 5
    if path.endswith((".tsx", ".jsx")):
        score += 4
    score += min(20, len(reverse_imports.get(path, [])) * 2)
    # docstring/comments → purpose استخراج راحت‌تر
    content = file_contents.get(path, "")
    if '"""' in content[:2000]:
        score += 3
    if "//" in content[:1000] or "#" in content[:1000]:
        score += 1
    # entry-point یا main file
    if any(k in path.lower() for k in ("main.py", "app.py", "page.tsx", "router")):
        score += 5
    return score


async def _ai_extract_purposes_batch(
    batch: List[Dict[str, Any]],
    verify_model_id: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """یک AI call روی batch از فایل‌ها برای purpose extraction."""
    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception as e:
        logger.debug(f"purpose_extractor: ai_manager import failed: {e}")
        return {}

    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            return {}

    files_block_parts = []
    for i, item in enumerate(batch):
        path = item["path"]
        content = item["content"][:_MAX_CONTENT_FOR_AI]
        ctx_extras = []
        if item.get("originating_task_id"):
            ctx_extras.append(f"از task#{item['originating_task_id']} ساخته شد")
        if item.get("first_seen_date"):
            ctx_extras.append(f"اولین commit: {item['first_seen_date']}")
        ctx_extras_str = " | ".join(ctx_extras) if ctx_extras else "(بدون context تاریخی)"

        files_block_parts.append(
            f"### [FILE {i}] {path}\n"
            f"📅 context: {ctx_extras_str}\n"
            f"```\n{content}\n```\n"
        )
    files_block = "\n".join(files_block_parts)

    prompt = (
        "تو یک Code Reviewer هستی. برای هر فایل زیر، **هدف کاری** و\n"
        "**رفتار مورد انتظار** را با دقت استخراج کن.\n\n"
        f"{files_block}\n\n"
        "⚠️ راهنما:\n"
        "- stated_purpose: یک جمله — این فایل چه کاری *قرار است* بکند\n"
        "  (از docstring، comments، نام تابع‌ها، خروجی استدلال کن)\n"
        "- expected_inputs: چه ورودی‌هایی می‌گیرد (data type یا منبع)\n"
        "- expected_outputs: چه خروجی تولید می‌کند\n"
        "- interacting_with: لیست modules/services/files که با این همکار است\n"
        "  (بر اساس imports یا function calls — حداکثر ۵ مورد)\n"
        "- main_responsibility: یک کلمه — verifier / scanner / service /\n"
        "  notifier / scheduler / repository / model / view / utility\n\n"
        "خروجی فقط JSON خالص بدون ``` :\n"
        "{\n"
        '  "results": [\n'
        '    {\n'
        '      "file_index": 0,\n'
        '      "stated_purpose": "...",\n'
        '      "expected_inputs": ["..."],\n'
        '      "expected_outputs": ["..."],\n'
        '      "interacting_with": ["..."],\n'
        '      "main_responsibility": "..."\n'
        '    },\n'
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
                max_tokens=3000,
                temperature=0.1,
                allow_fallback=True,
            ),
            timeout=_AI_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        logger.warning("purpose_extractor: AI timeout")
        return {}
    except Exception as e:
        logger.warning(f"purpose_extractor: AI call failed: {e}")
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
    if not isinstance(results, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("file_index"))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(batch):
            continue
        path = batch[idx]["path"]
        out[path] = {
            "stated_purpose": str(item.get("stated_purpose", ""))[:500],
            "expected_inputs": [str(x)[:100] for x in (item.get("expected_inputs") or [])][:8],
            "expected_outputs": [str(x)[:100] for x in (item.get("expected_outputs") or [])][:8],
            "interacting_with": [str(x)[:100] for x in (item.get("interacting_with") or [])][:8],
            "main_responsibility": str(item.get("main_responsibility", ""))[:80],
        }
    return out


def _build_creation_context(
    path: str,
    task_history: List[Dict[str, Any]],
    commit_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """creation_context برای یک فایل — کِی، چرا، توسط کدام task ساخته شد."""
    out: Dict[str, Any] = {
        "first_seen_commit": None,
        "first_seen_date": None,
        "originating_task_id": None,
        "originating_raw_idea": None,
        "modifying_tasks": [],
    }
    # earliest commit touching this path
    earliest = None
    for c in commit_history:
        files = c.get("files") or []
        if any(path in (f.get("filename") or "") for f in files if isinstance(f, dict)):
            if earliest is None or (c.get("date", "") < earliest.get("date", "9999")):
                earliest = c
    if earliest:
        out["first_seen_commit"] = earliest.get("sha", "")[:7]
        out["first_seen_date"] = earliest.get("date", "")

    # task هایی که این فایل را در target_files دارند
    for t in task_history:
        if path in (t.get("target_files") or []):
            if out["originating_task_id"] is None:
                out["originating_task_id"] = t.get("id")
                out["originating_raw_idea"] = (t.get("raw_idea") or "")[:300]
            out["modifying_tasks"].append(t.get("id"))
    out["modifying_tasks"] = out["modifying_tasks"][:10]
    return out


async def extract_purposes(
    inventory: Dict[str, Any],
    file_contents: Dict[str, str],
    reverse_imports: Optional[Dict[str, List[str]]] = None,
    task_history: Optional[List[Dict[str, Any]]] = None,
    commit_history: Optional[List[Dict[str, Any]]] = None,
    verify_model_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """ساخت purpose_map برای فایل‌های مهم.

    Args:
        inventory: خروجی build_inventory
        file_contents: محتوای فایل‌ها
        reverse_imports: {path: [paths_that_import_this]} از import_graph
        task_history: لیست task های قبلی این پروژه (برای originating_task_id)
        commit_history: لیست commits اخیر
        verify_model_id: مدل AI برای purpose extraction

    Returns:
        {file_path: purpose_dict}
    """
    reverse_imports = reverse_imports or {}
    task_history = task_history or []
    commit_history = commit_history or []

    # رتبه‌بندی فایل‌ها برای انتخاب MAX_FILES_TO_PURPOSE تای بالاتر
    scored: List[tuple] = []
    for path in file_contents.keys():
        score = _file_importance_score(path, file_contents, reverse_imports)
        if score > 0:
            scored.append((score, path))
    scored.sort(key=lambda x: -x[0])
    top_paths = [p for _, p in scored[:_MAX_FILES_TO_PURPOSE]]

    # batch AI calls
    purpose_map: Dict[str, Dict[str, Any]] = {}
    for batch_start in range(0, len(top_paths), _AI_BATCH_SIZE):
        batch_paths = top_paths[batch_start:batch_start + _AI_BATCH_SIZE]
        batch = []
        for path in batch_paths:
            ctx = _build_creation_context(path, task_history, commit_history)
            batch.append({
                "path": path,
                "content": file_contents.get(path, ""),
                "originating_task_id": ctx.get("originating_task_id"),
                "first_seen_date": ctx.get("first_seen_date"),
            })
        try:
            ai_results = await _ai_extract_purposes_batch(batch, verify_model_id)
        except Exception as e:
            logger.warning(f"purpose batch failed: {e}")
            ai_results = {}

        for path in batch_paths:
            ctx = _build_creation_context(path, task_history, commit_history)
            ai_data = ai_results.get(path, {})
            # current_usage از reverse_imports
            current_usage = (
                f"{len(reverse_imports.get(path, []))} reverse-imports"
                if reverse_imports.get(path) is not None else "unknown"
            )
            purpose_map[path] = {
                "stated_purpose": ai_data.get("stated_purpose", ""),
                "evidence_sources": [
                    src for src, present in [
                        ("comments", bool(re.search(r"^\s*#|^\s*//", file_contents.get(path, "")[:3000], re.MULTILINE))),
                        ("docstrings", '"""' in file_contents.get(path, "")[:3000]),
                        ("task_history", bool(ctx.get("originating_task_id"))),
                        ("commit_messages", bool(ctx.get("first_seen_commit"))),
                    ] if present
                ],
                "expected_inputs": ai_data.get("expected_inputs", []),
                "expected_outputs": ai_data.get("expected_outputs", []),
                "interacting_with": ai_data.get("interacting_with", []),
                "main_responsibility": ai_data.get("main_responsibility", ""),
                "creation_context": ctx,
                "current_usage": current_usage,
                "importance_score": next((s for s, p in scored if p == path), 0),
            }

    return purpose_map
