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

🆕 (Phase 5 — bug 23) — Ripple Analysis توسعه‌یافته:
  - analyze_change_impact: downstream (dependents) — قبلاً
  - analyze_upstream_impact: upstream (dependencies) — جدید
  - analyze_added_files_ripple: ADDs (orphan + companion) — جدید
  - Limits depth-aware (quick=10، deep=30، ultra=60)

API:
    build_bidirectional_deps(import_graph, imported_by) -> Dict[path, ...]
    analyze_change_impact(delta, deps, purpose_map, file_contents,
                          verify_model_id, max_changed) -> List[Dict]
    analyze_upstream_impact(delta, deps, purpose_map, file_contents,
                            verify_model_id, max_changed) -> List[Dict]
    analyze_added_files_ripple(delta, deps, inventory, file_contents,
                               verify_model_id, max_added) -> List[Dict]
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 🆕 (Phase 5 — bug 23) — defaults نرم شد. caller می‌تواند با max_changed
# override کند (depth-aware در oversight_deep_scan_service).
_MAX_CHANGED_FILES = 30  # قبلاً ۱۰ بود — برای repo های فعال خیلی کم
_MAX_ADDED_FILES = 25
_AI_TIMEOUT_S = 30
_MAX_DEPENDENTS_PER_FILE = 12  # قبلاً ۸ بود
_MAX_DEPENDENCIES_PER_FILE = 12


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
    max_changed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """تحلیل impact هر change روی dependents.

    برای هر changed file (modify, signature_change):
      - dependents را پیدا کن
      - AI تصمیم می‌گیرد آیا dependent با این تغییر inconsistent می‌شود
      - اگر بله، task pending با reason صریح

    Returns:
        [{"changed_file", "dependent_file", "risk", "reason", "recommended_action"}, ...]
    """
    # 🆕 (bug 23) — caller می‌تواند سقف را override کند
    _max = int(max_changed) if max_changed and max_changed > 0 else _MAX_CHANGED_FILES

    # جمع‌آوری changed files از delta
    changed: List[Dict[str, Any]] = []
    for item in delta.get("modify", [])[:_max]:
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
    for ch in changed[:_max]:
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


# ============================================================
# 🆕 (Phase 5 — bug 23) — Upstream Impact Analysis
# ============================================================

async def analyze_upstream_impact(
    delta: Dict[str, List[Dict[str, Any]]],
    deps: Dict[str, Dict[str, List[str]]],
    purpose_map: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
    verify_model_id: Optional[str] = None,
    max_changed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """تحلیل تأثیر بالادست: وقتی فایلی تغییر کرد، آیا upstream های (deps)
    نیز نیاز به به‌روزرسانی دارند؟

    مثال: اگر `routes/auth.py` تغییر کرد و حالا از `services/jwt.py`
    یک متد جدید فراخوانی می‌کند که آنجا وجود ندارد → finding برای
    اضافه‌کردن آن متد در `services/jwt.py`.

    معکوس analyze_change_impact است.
    """
    _max = int(max_changed) if max_changed and max_changed > 0 else _MAX_CHANGED_FILES

    changed: List[Dict[str, Any]] = []
    for item in delta.get("modify", [])[:_max]:
        changed.append({"path": item["path"], "kind": "modify"})
    for item in delta.get("signature_change", []):
        changed.append({"path": item["path"], "kind": "signature_change"})

    if not changed:
        return []

    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
        if not verify_model_id:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
    except Exception:
        verify_model_id = None

    impacts: List[Dict[str, Any]] = []
    for ch in changed[:_max]:
        path = ch["path"]
        upstream = deps.get(path, {}).get("dependencies", [])[:_MAX_DEPENDENCIES_PER_FILE]
        if not upstream:
            continue
        # خود upstream ها هم اگر در delta.modify بودند، رد می‌کنیم —
        # چون احتمالاً همراه با changed file به‌روز شده‌اند.
        modified_set = {m["path"] for m in delta.get("modify", [])}
        upstream = [u for u in upstream if u not in modified_set]
        if not upstream:
            continue

        changed_content = file_contents.get(path, "")[:5000]
        upstream_summary = "\n".join(
            f"- {u}: {(purpose_map.get(u, {}).get('stated_purpose') or 'بدون purpose')[:150]}"
            for u in upstream
        )

        if not verify_model_id:
            for u in upstream:
                impacts.append({
                    "changed_file": path,
                    "change_kind": ch["kind"],
                    "upstream_file": u,
                    "risk": "unknown",
                    "reason": "AI تحلیل در دسترس نیست — manual review توصیه می‌شود",
                    "recommended_action": "manual_review",
                })
            continue

        prompt = (
            f"یک فایل تغییر کرده. وظیفه‌ات: تحلیل کن آیا فایل‌های upstream "
            f"(چیزهایی که این فایل import می‌کند) نیاز به به‌روزرسانی دارند.\n\n"
            f"📄 changed file: {path}\n"
            f"تغییر: {ch['kind']}\n"
            f"محتوای فعلی (اول ۵ هزار char):\n```\n{changed_content}\n```\n\n"
            f"📋 upstream files (که این فایل import می‌کند):\n"
            f"{upstream_summary}\n\n"
            "برای هر upstream، تحلیل کن:\n"
            "- آیا changed file حالا از API یا behavior جدیدی استفاده می‌کند که upstream فعلی پشتیبانی نمی‌کند؟\n"
            "- آیا upstream باید تابع/متد/فیلد جدید اضافه کند تا changed file درست کار کند؟\n"
            "- ریسک: high (شکستن) / medium (نیاز به update) / low (پایدار)\n"
            "- اقدام: needs_update | needs_review | no_action\n\n"
            "اگر مطمئن نیستی، 'no_action' برگردان — false-positive نمی‌خواهیم.\n\n"
            "خروجی JSON خالص:\n"
            "{\n"
            '  "impacts": [\n'
            '    {"upstream": "path", "risk": "high|medium|low", "reason": "...", "action": "needs_update|needs_review|no_action"},\n'
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
                _action = str(imp.get("action", "")).lower()
                if _action == "no_action":
                    continue  # فقط مواردی که نیاز به اقدام دارند ذخیره می‌شوند
                impacts.append({
                    "changed_file": path,
                    "change_kind": ch["kind"],
                    "upstream_file": str(imp.get("upstream", ""))[:200],
                    "risk": str(imp.get("risk", "unknown")).lower(),
                    "reason": str(imp.get("reason", ""))[:400],
                    "recommended_action": _action or "needs_review",
                })
        except Exception as e:
            logger.warning(f"upstream impact analysis failed for {path}: {e}")
            # silent fail-soft — بدون false-positive
            continue

    return impacts


# ============================================================
# 🆕 (Phase 5 — bug 23) — Added Files Ripple Analysis
# ============================================================

def _expected_companions(path: str) -> List[Dict[str, str]]:
    """heuristic: برای یک فایل، companion هایی که باید وجود داشته باشند را
    پیشنهاد می‌دهد. خروجی: [{kind, path}].

    Examples:
      backend/app/services/foo.py → backend/tests/test_foo.py
      backend/app/api/routes/bar.py → فرانت‌اند باید fetch داشته باشد
      frontend/src/app/baz/page.tsx → باید Link/nav داشته باشد
    """
    out: List[Dict[str, str]] = []
    p = path.replace("\\", "/")
    base = os.path.basename(p)
    name_no_ext = os.path.splitext(base)[0]

    if p.startswith("backend/app/services/") and p.endswith(".py") and not base.startswith("_"):
        out.append({
            "kind": "test_file",
            "path": f"backend/tests/test_{name_no_ext}.py",
            "reason": "service ها باید unit test همراه داشته باشند",
        })
    elif p.startswith("backend/app/api/routes/") and p.endswith(".py"):
        out.append({
            "kind": "frontend_consumer",
            "path": "frontend/src/**",
            "reason": "endpoint جدید باید توسط حداقل یک frontend page مصرف شود (یا dead-endpoint شناخته خواهد شد)",
        })
        out.append({
            "kind": "test_file",
            "path": f"backend/tests/test_{name_no_ext}.py",
            "reason": "endpoint route باید integration test داشته باشد",
        })
    elif p.startswith("frontend/src/app/") and base == "page.tsx":
        # frontend page
        out.append({
            "kind": "navigation_entry",
            "path": "frontend/src/components/Nav* | layout.tsx",
            "reason": "page جدید باید از nav یا Link قابل دسترسی باشد، وگرنه dead-route خواهد بود",
        })
    elif p.startswith("backend/app/models/") and p.endswith(".py"):
        out.append({
            "kind": "migration",
            "path": "backend/alembic/versions/*",
            "reason": "model جدید معمولاً نیاز به migration دارد",
        })
    return out


async def analyze_added_files_ripple(
    delta: Dict[str, List[Dict[str, Any]]],
    deps: Dict[str, Dict[str, List[str]]],
    inventory: Dict[str, Any],
    file_contents: Dict[str, str],
    verify_model_id: Optional[str] = None,
    max_added: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """برای هر ADDed file، companion های مورد انتظار را چک می‌کند.

    دو نوع finding:
      1. orphan: هیچ فایلی این را import نکرده + entry-point نیست
      2. missing_companion: companion پیش‌بینی‌شده (test/migration/nav) ندارد
    """
    _max = int(max_added) if max_added and max_added > 0 else _MAX_ADDED_FILES
    adds = delta.get("add", [])
    if not adds:
        return []

    # همهٔ مسیرها برای lookup
    all_paths: set = set()
    try:
        all_files_list = inventory.get("files") or []
        for f in all_files_list:
            if isinstance(f, dict):
                all_paths.add(str(f.get("path") or "").replace("\\", "/"))
            elif isinstance(f, str):
                all_paths.add(f.replace("\\", "/"))
    except Exception:
        pass
    # fallback: deps + contents
    all_paths.update(deps.keys())
    all_paths.update(file_contents.keys())

    findings: List[Dict[str, Any]] = []
    _ENTRY_POINTS = {"backend/app/main.py", "backend/main.py"}

    for item in adds[:_max]:
        path = (item.get("path") if isinstance(item, dict) else str(item)) or ""
        path = path.replace("\\", "/")
        if not path:
            continue

        # orphan check (skip entry-points and obvious config/static)
        is_code = path.endswith((".py", ".tsx", ".ts", ".jsx", ".js"))
        if is_code and path not in _ENTRY_POINTS:
            dependents = deps.get(path, {}).get("dependents", [])
            # frontend page.tsx معمولاً import نمی‌شود — توسط router کشف می‌شود
            is_frontend_page = (
                path.startswith("frontend/src/app/")
                and os.path.basename(path) in ("page.tsx", "layout.tsx", "route.ts")
            )
            if not dependents and not is_frontend_page:
                findings.append({
                    "added_file": path,
                    "issue_type": "orphan_added",
                    "risk": "medium",
                    "reason": "این فایل جدید اضافه شده ولی هیچ فایل دیگری آن را import نمی‌کند — احتمالاً wiring فراموش شده یا dead-on-arrival است.",
                    "recommended_action": "needs_wiring",
                    "expected_partners": [],
                })

        # companion check
        expected = _expected_companions(path)
        for comp in expected:
            comp_path = comp["path"]
            # برای glob patterns مثل frontend/src/** فقط هشدار می‌دهیم
            if "*" in comp_path:
                # نمی‌توانیم دقیق چک کنیم؛ پس heuristic: آیا فایلی هست که نام route فایل را reference کند؟
                # برای route ها: نام endpoint را در content فایل‌های frontend بگرد
                if comp["kind"] == "frontend_consumer" and path.startswith("backend/app/api/routes/"):
                    route_name = os.path.splitext(os.path.basename(path))[0]
                    found_consumer = False
                    for fpath, content in file_contents.items():
                        if fpath.startswith("frontend/") and route_name in (content or ""):
                            found_consumer = True
                            break
                    if not found_consumer:
                        findings.append({
                            "added_file": path,
                            "issue_type": "missing_companion",
                            "companion_kind": comp["kind"],
                            "companion_path": comp_path,
                            "risk": "medium",
                            "reason": comp["reason"],
                            "recommended_action": "needs_companion",
                            "expected_partners": [comp_path],
                        })
                elif comp["kind"] == "navigation_entry":
                    # برای page.tsx، نام مسیر را در nav/layout بگرد
                    page_dir = os.path.dirname(path).replace("frontend/src/app/", "")
                    found_nav = False
                    for fpath, content in file_contents.items():
                        is_nav_file = (
                            "nav" in fpath.lower()
                            or fpath.endswith("layout.tsx")
                            or "Sidebar" in fpath
                        )
                        if is_nav_file and page_dir and page_dir in (content or ""):
                            found_nav = True
                            break
                    if not found_nav and page_dir:
                        findings.append({
                            "added_file": path,
                            "issue_type": "missing_companion",
                            "companion_kind": comp["kind"],
                            "companion_path": comp_path,
                            "risk": "low",
                            "reason": comp["reason"],
                            "recommended_action": "needs_companion",
                            "expected_partners": [comp_path],
                        })
                continue

            # مسیر صریح — وجود را چک کن
            if comp_path not in all_paths:
                findings.append({
                    "added_file": path,
                    "issue_type": "missing_companion",
                    "companion_kind": comp["kind"],
                    "companion_path": comp_path,
                    "risk": "low" if comp["kind"] == "test_file" else "medium",
                    "reason": comp["reason"],
                    "recommended_action": "needs_companion",
                    "expected_partners": [comp_path],
                })

    return findings
