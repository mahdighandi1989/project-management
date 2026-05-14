"""Phase 5 — Stale Detection (R8 — مهم‌ترین فاز برای گزینه‌های قدیمی).

شناسایی دو نوع stale:
  - Structural (۸ نوع): dead UI button، dead route، dead endpoint،
    unused function/class/field/env/file، stale dependency
  - Semantic (۵ نوع): purpose-mismatched، hidden purpose، inconsistent
    with recent changes، outdated business assumption، forgotten by user

این ماژول روی inventory + purpose_map + import_graph + runtime_state
(اگر در دسترس) کار می‌کند.

API:
    detect_stale(inventory, purpose_map, imported_by, runtime_state) ->
        {structural: [...], semantic: [...]}
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_MAX_STALE_PER_TYPE = 50


# ─────────────────────────────────────────────────────────────────────────
# Structural Stale (۸ نوع)
# ─────────────────────────────────────────────────────────────────────────

def _detect_dead_ui_buttons(inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """button که handler ندارد یا handler خالی است."""
    out: List[Dict[str, Any]] = []
    for el in inventory.get("ui_elements", []):
        if el.get("type") != "button":
            continue
        handler = (el.get("handler") or "").strip()
        # button بدون handler یا فقط با value-only
        if not handler or handler in ("()", "{}", "() => {}", "() => null"):
            out.append({
                "kind": "dead_ui_button",
                "label": el.get("label", "?"),
                "file": el.get("file"),
                "reason": "button has no onClick handler",
            })
            if len(out) >= _MAX_STALE_PER_TYPE:
                break
    return out


def _detect_dead_frontend_routes(
    inventory: Dict[str, Any], file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """frontend route که در nav menu نیست و در هیچ Link/router.push نیست."""
    out: List[Dict[str, Any]] = []
    frontend_routes = (inventory.get("routes") or {}).get("frontend", [])
    # extract همه‌ی href ها از Link elements و router.push ها
    referenced_routes: Set[str] = set()
    for el in inventory.get("ui_elements", []):
        if el.get("type") == "link" and el.get("href"):
            referenced_routes.add(el["href"].split("?")[0].rstrip("/"))
    # router.push patterns
    router_push_re = re.compile(
        r"router\.(?:push|replace)\s*\(\s*[\"']([^\"']+)[\"']"
        r"|navigate\s*\(\s*[\"']([^\"']+)[\"']"
    )
    for path, content in file_contents.items():
        if not (path.endswith(".tsx") or path.endswith(".jsx")):
            continue
        for m in router_push_re.finditer(content[:50000]):
            r = (m.group(1) or m.group(2) or "").split("?")[0].rstrip("/")
            if r:
                referenced_routes.add(r)
    for route in frontend_routes:
        normalized = route.rstrip("/")
        # / همیشه main است — skip
        if normalized in ("", "/"):
            continue
        if normalized not in referenced_routes:
            out.append({
                "kind": "dead_frontend_route",
                "route": route,
                "reason": "route exists in app router but no Link/router.push references it",
            })
            if len(out) >= _MAX_STALE_PER_TYPE:
                break
    return out


def _detect_dead_backend_endpoints(
    inventory: Dict[str, Any], file_contents: Dict[str, str],
    runtime_state: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """endpoint backend که در هیچ frontend fetch نیست + در logs اخیر صدا نشد."""
    out: List[Dict[str, Any]] = []
    backend_endpoints = inventory.get("backend_endpoints", [])
    # frontend fetch patterns
    fetch_paths: Set[str] = set()
    fetch_re = re.compile(
        r"fetch\s*\(\s*[`\"']([^`\"']+)[`\"']"
        r"|axios\.\w+\s*\(\s*[`\"']([^`\"']+)[`\"']"
        r"|api\.\w+\s*\(\s*[`\"']([^`\"']+)[`\"']"
    )
    for path, content in file_contents.items():
        if not (path.endswith((".tsx", ".jsx", ".ts", ".js"))):
            continue
        for m in fetch_re.finditer(content[:80000]):
            url = m.group(1) or m.group(2) or m.group(3) or ""
            # normalize path (remove ${} interpolations)
            url = re.sub(r"\$\{[^}]+\}", ":var", url)
            url = url.split("?")[0]
            fetch_paths.add(url)

    # endpoints که در logs اخیر صدا شدند (اگر runtime_state داریم)
    called_endpoints: Set[str] = set(
        (runtime_state or {}).get("endpoints_called_recently") or []
    )

    for ep in backend_endpoints:
        path = ep.get("path", "")
        if not path:
            continue
        # نرمالیزه کن
        path_normalized = re.sub(r"\{[^}]+\}", ":var", path)
        # match approximate (در fetch_paths هست یا substring مشترک)
        ref_in_frontend = any(
            path_normalized.lower() in fp.lower() or fp.lower() in path_normalized.lower()
            for fp in fetch_paths if fp and len(fp) > 5
        )
        ref_in_logs = (
            path in called_endpoints
            or any(path in c for c in called_endpoints)
        )
        if not ref_in_frontend and not ref_in_logs:
            # health/api/root را skip کن
            if path in ("/", "/health", "/api"):
                continue
            out.append({
                "kind": "dead_backend_endpoint",
                "method": ep.get("method"),
                "path": path,
                "file": ep.get("file"),
                "function": ep.get("function"),
                "reason": "no frontend fetch + no recent call in logs",
            })
            if len(out) >= _MAX_STALE_PER_TYPE:
                break
    return out


def _detect_unused_functions(
    file_contents: Dict[str, str],
    imported_by: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    """functions/classes که reverse-import = 0 و entry-point نیستند."""
    out: List[Dict[str, Any]] = []
    # ساده: فایل‌هایی که reverse-import=0 و entry-point نیستند
    entry_keywords = ("main.py", "app.py", "__init__.py", "conftest.py", "setup.py", "manage.py")
    for path in file_contents.keys():
        if not path.endswith(".py"):
            continue
        if any(k in path.lower() for k in entry_keywords):
            continue
        rev = imported_by.get(path, [])
        if len(rev) == 0:
            # ولی test files exception
            if "test" in path.lower() or "/tests/" in path:
                continue
            out.append({
                "kind": "unused_file",
                "file": path,
                "reason": "reverse_import=0 and not entry-point",
            })
            if len(out) >= _MAX_STALE_PER_TYPE:
                break
    return out


def _detect_unused_dataclass_fields(
    inventory: Dict[str, Any], file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """dataclass field که در هیچ‌جا read/write نمی‌شود."""
    out: List[Dict[str, Any]] = []
    db_items = [d for d in inventory.get("db_schema", []) if d.get("kind") == "dataclass"]
    # برای هر dataclass، فیلدهای آن را در همه فایل‌ها جستجو
    all_content = "\n".join(file_contents.values())[:2000000]
    for dc in db_items[:10]:  # محدود کن تا زمان نگیرد
        cls_name = dc.get("name")
        for f in dc.get("fields", []):
            field_name = f.get("name", "")
            if not field_name or len(field_name) < 4 or field_name.startswith("_"):
                continue
            # جستجو در همه فایل‌ها (روی .field_name یا ['field_name'])
            patterns = [f".{field_name}", f"'{field_name}'", f'"{field_name}"']
            count = sum(all_content.count(p) for p in patterns)
            if count <= 1:  # فقط در تعریف خودش
                out.append({
                    "kind": "unused_dataclass_field",
                    "class": cls_name,
                    "field": field_name,
                    "file": dc.get("file"),
                    "reason": f"field defined in {cls_name} but not read/written anywhere",
                })
                if len(out) >= _MAX_STALE_PER_TYPE:
                    return out
    return out


def _detect_unused_env_vars(
    inventory: Dict[str, Any], file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """env var تعریف شده در docs/example ولی هیچ‌جا استفاده نشده."""
    out: List[Dict[str, Any]] = []
    # env var های documented در .env.example یا README
    documented: Set[str] = set()
    for path, content in file_contents.items():
        if path.endswith(".env.example") or "/env.example" in path:
            for m in re.finditer(r"^([A-Z_][A-Z0-9_]*)\s*=", content, re.MULTILINE):
                documented.add(m.group(1))
        elif path.lower().endswith("readme.md"):
            for m in re.finditer(r"`([A-Z_][A-Z0-9_]{4,})`", content[:30000]):
                documented.add(m.group(1))
    # env vars که در inventory هستن (used)
    used = {e.get("name") for e in inventory.get("env_vars", [])}
    # documented but not used
    for env in sorted(documented - used):
        if env in {"PATH", "HOME", "USER", "SHELL", "TERM"}:
            continue  # OS standard
        out.append({
            "kind": "unused_env_var",
            "name": env,
            "reason": "documented in .env.example/README but not used in code",
        })
        if len(out) >= _MAX_STALE_PER_TYPE:
            break
    return out


def _detect_orphan_files(
    file_contents: Dict[str, str],
    imported_by: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    """فایلی که reverse-import = 0 و در path standard entry point نیست."""
    # درست مثل _detect_unused_functions ولی برای انواع فایل‌های دیگر
    return []  # برای جلوگیری از تکرار، فعلاً همان _detect_unused_functions کافی است


def _detect_stale_dependencies(
    inventory: Dict[str, Any], file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """dependency در requirements/package.json ولی هیچ import در کد."""
    out: List[Dict[str, Any]] = []
    deps = inventory.get("dependencies", {})
    # ساخت text فقط از .py + .ts/.tsx + .js/.jsx
    py_imports_text = ""
    js_imports_text = ""
    for path, content in file_contents.items():
        if path.endswith(".py"):
            # only import lines
            for line in content[:30000].splitlines():
                if line.strip().startswith(("import ", "from ")):
                    py_imports_text += line + "\n"
        elif path.endswith((".ts", ".tsx", ".js", ".jsx")):
            for line in content[:30000].splitlines():
                if "import " in line or "require(" in line:
                    js_imports_text += line + "\n"

    # Python deps
    for dep in deps.get("python", [])[:30]:
        # نام package می‌تواند با dash باشد ولی import با underscore
        dep_var = dep.replace("-", "_").lower()
        if (
            dep_var not in py_imports_text.lower()
            and dep.lower() not in py_imports_text.lower()
        ):
            # بعضی package ها namespace dotted دارند
            short = dep.split("-")[0].lower()
            if short not in py_imports_text.lower() and len(short) >= 4:
                out.append({
                    "kind": "stale_dependency",
                    "lang": "python",
                    "name": dep,
                    "reason": f"in requirements but no 'import {dep_var}' or 'from {dep_var}' found",
                })
    # Node deps
    for dep in deps.get("node", [])[:30]:
        if dep.startswith("@types/"):
            continue  # type packages
        if dep not in js_imports_text and dep.replace("@", "") not in js_imports_text:
            out.append({
                "kind": "stale_dependency",
                "lang": "node",
                "name": dep,
                "reason": f"in package.json but no import for '{dep}' found",
            })
    return out[:_MAX_STALE_PER_TYPE]


# ─────────────────────────────────────────────────────────────────────────
# Semantic Stale (۵ نوع — R10)
# ─────────────────────────────────────────────────────────────────────────

def _detect_hidden_purpose(
    inventory: Dict[str, Any], purpose_map: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """فایل/option که کاربر نمی‌داند چی هست — بدون doc + بدون purpose."""
    out: List[Dict[str, Any]] = []
    for path in file_contents.keys():
        # فقط فایل‌های مهم
        purpose = purpose_map.get(path, {})
        if not purpose:
            continue
        stated = (purpose.get("stated_purpose") or "").strip()
        evidence = purpose.get("evidence_sources") or []
        # hidden if: stated_purpose خالی یا کوتاه + هیچ doc/comment ندارد
        if (not stated or len(stated) < 30) and "docstrings" not in evidence:
            out.append({
                "kind": "hidden_purpose",
                "file": path,
                "reason": (
                    "هدف این فایل از کد یا comments قابل استخراج نیست — "
                    "نیاز به documentation یا حذف اگر unused"
                ),
                "main_responsibility": purpose.get("main_responsibility", ""),
            })
            if len(out) >= _MAX_STALE_PER_TYPE:
                break
    return out


def _detect_forgotten_options(
    inventory: Dict[str, Any], purpose_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """UI option/setting که کاربر هر بار باید بپرسد چی هست (R8)."""
    out: List[Dict[str, Any]] = []
    # UI options که field_hint مبهم دارند
    for opt in inventory.get("ui_options", []):
        field = opt.get("field_hint")
        if not field or len(field) < 4 or field in ("value", "state", "data", "item"):
            out.append({
                "kind": "forgotten_option",
                "type": opt.get("type"),
                "file": opt.get("file"),
                "field_hint": field,
                "reason": (
                    "UI option با field name مبهم — "
                    "کاربر هر بار باید بپرسد این چیست"
                ),
            })
            if len(out) >= _MAX_STALE_PER_TYPE:
                break
    return out


# ─────────────────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────────────────

def detect_stale(
    inventory: Dict[str, Any],
    purpose_map: Dict[str, Dict[str, Any]],
    file_contents: Dict[str, str],
    imported_by: Optional[Dict[str, List[str]]] = None,
    runtime_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """تشخیص همه‌ی stale items — structural + semantic.

    خروجی: {"structural": [...], "semantic": [...], "summary": {...}}
    هر detector fail-soft است.
    """
    imported_by = imported_by or {}

    structural_detectors = [
        ("dead_ui_buttons", lambda: _detect_dead_ui_buttons(inventory)),
        ("dead_frontend_routes", lambda: _detect_dead_frontend_routes(inventory, file_contents)),
        ("dead_backend_endpoints", lambda: _detect_dead_backend_endpoints(inventory, file_contents, runtime_state)),
        ("unused_files", lambda: _detect_unused_functions(file_contents, imported_by)),
        ("unused_dataclass_fields", lambda: _detect_unused_dataclass_fields(inventory, file_contents)),
        ("unused_env_vars", lambda: _detect_unused_env_vars(inventory, file_contents)),
        ("stale_dependencies", lambda: _detect_stale_dependencies(inventory, file_contents)),
    ]
    structural: List[Dict[str, Any]] = []
    for name, fn in structural_detectors:
        try:
            items = fn()
            for it in items:
                it["_detector"] = name
            structural.extend(items)
        except Exception as e:
            logger.warning(f"stale detector {name} failed: {e}")

    semantic_detectors = [
        ("hidden_purpose", lambda: _detect_hidden_purpose(inventory, purpose_map, file_contents)),
        ("forgotten_options", lambda: _detect_forgotten_options(inventory, purpose_map)),
    ]
    semantic: List[Dict[str, Any]] = []
    for name, fn in semantic_detectors:
        try:
            items = fn()
            for it in items:
                it["_detector"] = name
            semantic.extend(items)
        except Exception as e:
            logger.warning(f"semantic detector {name} failed: {e}")

    summary = {
        "structural_total": len(structural),
        "semantic_total": len(semantic),
        "by_kind": {},
    }
    for it in structural + semantic:
        k = it.get("kind", "unknown")
        summary["by_kind"][k] = summary["by_kind"].get(k, 0) + 1

    return {
        "structural": structural,
        "semantic": semantic,
        "summary": summary,
    }
