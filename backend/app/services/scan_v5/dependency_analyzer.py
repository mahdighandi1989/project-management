"""Phase 5 — Bidirectional Dependency Analyzer (R7 صریح).

برای هر فایل، **هر دو طرف** dependency استخراج می‌کند:
  - forward (dependencies): این فایل به چه چیزی import می‌کند
  - reverse (dependents): چه چیزهایی این فایل را import می‌کنند

علاوه بر import-based، **logical** dependency هم تشخیص می‌دهد (با AI):
  - logical_dependencies: کدام components روی این تکیه دارند
  - logical_dependents: این از کدام components انتظار دارد

و Logical Impact Analysis (R10):
  - برای هر changed file، dependents در خطر را شناسایی کن
  - AI تحلیل کند آیا dependent نیاز به update دارد

API:
    build_bidirectional_deps(import_graph, imported_by) -> Dict[path, ...]
    analyze_change_impact(delta, deps, purpose_map, file_contents,
                          verify_model_id) -> List[Dict]
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MAX_CHANGED_FILES = 10  # محدودیت برای AI cost
_AI_TIMEOUT_S = 30
_MAX_DEPENDENTS_PER_FILE = 8


def build_bidirectional_deps(
    imports: Dict[str, List[str]],
    imported_by: Dict[str, List[str]],
) -> Dict[str, Dict[str, List[str]]]:
    """ترکیب forward + reverse برای هر فایل.

    Args:
        imports: {file → [files it imports]}
        imported_by: {file → [files that import it]}

    Returns:
        {file → {"dependencies": [...], "dependents": [...]}}
    """
    all_files = set(imports.keys()) | set(imported_by.keys())
    out: Dict[str, Dict[str, List[str]]] = {}
    for f in all_files:
        out[f] = {
            "dependencies": imports.get(f, []),
            "dependents": imported_by.get(f, []),
        }
    return out


async def analyze_change_impact(
    delta: Dict[str, List[Dict[str, Any]]],
    deps: Dict[str, Dict[str, List[str]]],
    purpose_map: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
    verify_model_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """تحلیل impact هر change روی dependents.

    برای هر changed file (modify, signature_change):
      - dependents را پیدا کن
      - AI تصمیم می‌گیرد آیا dependent با این تغییر inconsistent می‌شود
      - اگر بله، task pending با reason صریح

    Returns:
        [{"changed_file", "dependent_file", "risk", "reason", "recommended_action"}, ...]
    """
    # جمع‌آوری changed files از delta
    changed: List[Dict[str, Any]] = []
    for item in delta.get("modify", [])[:_MAX_CHANGED_FILES]:
        changed.append({"path": item["path"], "kind": "modify"})
    for item in delta.get("signature_change", []):
        changed.append({"path": item["path"], "kind": "signature_change"})
    # rename و move هم می‌توانند impact داشته باشند ولی low priority
    for item in delta.get("rename", []):
        changed.append({
            "path": item["to"], "kind": "rename",
            "from": item.get("from"),
        })

    if not changed:
        return []

    # برای هر changed، dependents پیدا کن
    impacts: List[Dict[str, Any]] = []
    for ch in changed[:_MAX_CHANGED_FILES]:
        path = ch["path"]
        dependents = deps.get(path, {}).get("dependents", [])[:_MAX_DEPENDENTS_PER_FILE]
        if not dependents:
            continue

        # محتوای changed file + dependents برای AI
        changed_content = file_contents.get(path, "")[:5000]
        dependents_summary = "\n".join(
            f"- {dep}: {(purpose_map.get(dep, {}).get('stated_purpose') or 'بدون purpose')[:150]}"
            for dep in dependents
        )

        # AI analysis
        try:
            from ..ai_manager import get_ai_manager
            from ..ai_base import Message
            if not verify_model_id:
                from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
                verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            verify_model_id = None

        if not verify_model_id:
            # fail-soft — همه dependents را به‌عنوان "needs_review" گزارش کن
            for dep in dependents:
                impacts.append({
                    "changed_file": path,
                    "change_kind": ch["kind"],
                    "dependent_file": dep,
                    "risk": "unknown",
                    "reason": "AI تحلیل در دسترس نیست — manual review توصیه می‌شود",
                    "recommended_action": "manual_review",
                })
            continue

        prompt = (
            f"یک فایل تغییر کرده. وظیفه‌ات: تحلیل کن آیا dependents در خطر هستند.\n\n"
            f"📄 changed file: {path}\n"
            f"تغییر: {ch['kind']}\n"
            f"محتوای فعلی (اول ۵ هزار char):\n```\n{changed_content}\n```\n\n"
            f"📋 dependents (فایل‌هایی که این را import می‌کنند):\n"
            f"{dependents_summary}\n\n"
            "برای هر dependent، تحلیل کن:\n"
            "- آیا تغییر این فایل ممکن است رفتار dependent را بشکند؟\n"
            "- ریسک: high (شکستن syntax/runtime) / medium (تغییر منطقی) / low (پایدار)\n"
            "- اقدام: needs_update | needs_review | no_action\n\n"
            "خروجی JSON خالص:\n"
            "{\n"
            '  "impacts": [\n'
            '    {"dependent": "path", "risk": "high|medium|low", "reason": "...", "action": "needs_update|needs_review|no_action"},\n'
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
                    max_tokens=1500,
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
                raise ValueError("no JSON")
            data = json.loads(raw[s:e + 1])
            for imp in (data.get("impacts") or []):
                if not isinstance(imp, dict):
                    continue
                impacts.append({
                    "changed_file": path,
                    "change_kind": ch["kind"],
                    "dependent_file": str(imp.get("dependent", ""))[:200],
                    "risk": str(imp.get("risk", "unknown")).lower(),
                    "reason": str(imp.get("reason", ""))[:400],
                    "recommended_action": str(imp.get("action", "needs_review")).lower(),
                })
        except Exception as e:
            logger.warning(f"impact analysis failed for {path}: {e}")
            # fallback
            for dep in dependents:
                impacts.append({
                    "changed_file": path,
                    "change_kind": ch["kind"],
                    "dependent_file": dep,
                    "risk": "unknown",
                    "reason": f"AI analysis failed: {str(e)[:100]}",
                    "recommended_action": "manual_review",
                })

    return impacts
