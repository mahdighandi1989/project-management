"""Phase 5 — Comprehensive Inventory (R3 — ریز تا درشت).

۱۲ لایه‌ی ساختاری از یک پروژه را inventory می‌کند:
  1. Files (همه)
  2. Backend endpoints (FastAPI routers + WebSocket + background tasks)
  3. UI elements (button, form, input, Link, modal triggers, dropdown)
  4. DB schema (dataclass + Column + migrations)
  5. Env vars (os.environ.get, os.getenv, process.env.X)
  6. Config files (.json, .yaml, .toml, .env*)
  7. Dependencies (requirements.txt, package.json)
  8. Scripts (.sh, pyproject scripts, package.json scripts)
  9. Cron/scheduled (apscheduler, BackgroundTasks, asyncio.create_task)
  10. Routes (frontend + backend)
  11. Notification calls (R12) — notify_event, send_telegram, bot.send_message
  12. UI options/settings (R8) — checkbox/slider/dropdown در UI + cross-ref WatchedProject

این ماژول روی **محتوای فایل‌ها** (که از GitHub fetched شده) کار می‌کند —
نه روی filesystem لوکال. Input: Dict[file_path, content].

API اصلی:
    build_inventory(file_contents, repo_paths) -> Dict[str, Any]
"""

from __future__ import annotations

import ast
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# محدودیت‌ها (حفاظت از payload بزرگ)
_MAX_ITEMS_PER_LAYER = 500
_MAX_CONTENT_SCAN = 200000  # هر فایل حداکثر 200KB scan شود


# ─────────────────────────────────────────────────────────────────────────
# Layer 2: Backend endpoints
# ─────────────────────────────────────────────────────────────────────────

_ROUTER_DECORATOR_RE = re.compile(
    r"@(?:router|app|api_router|sub_router)\.(get|post|put|patch|delete|websocket)"
    r"\s*\(\s*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
_BACKGROUND_TASK_RE = re.compile(
    r"BackgroundTasks?\(\)|"
    r"background_tasks\.add_task\(\s*([a-zA-Z_][a-zA-Z0-9_.]*)",
)
_WEBSOCKET_RE = re.compile(
    r"@(?:router|app)\.websocket\s*\(\s*[\"']([^\"']+)[\"']",
)


def _extract_backend_endpoints(
    file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    """همه‌ی FastAPI endpoint ها + WebSocket + background tasks."""
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        if "router" not in content and "app." not in content:
            continue
        content = content[:_MAX_CONTENT_SCAN]
        # HTTP endpoints + WebSocket
        for m in _ROUTER_DECORATOR_RE.finditer(content):
            method = m.group(1).upper()
            route = m.group(2)
            # تابع زیر decorator را پیدا کن
            tail = content[m.end():m.end() + 600]
            fn_m = re.search(r"(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)", tail)
            fn_name = fn_m.group(1) if fn_m else None
            out.append({
                "method": method,
                "path": route,
                "file": path,
                "function": fn_name,
            })
            if len(out) >= _MAX_ITEMS_PER_LAYER:
                return out
        # standalone WebSocket (دیده نشده در ROUTER_DECORATOR_RE اگر sub format)
        for m in _WEBSOCKET_RE.finditer(content):
            route = m.group(1)
            # ممکن است duplicate باشد، چک
            if not any(e["path"] == route and e["method"] == "WEBSOCKET" for e in out):
                out.append({"method": "WEBSOCKET", "path": route, "file": path})
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 3: UI elements
# ─────────────────────────────────────────────────────────────────────────

# 🆕 (Phase 5 — bug 15) — قبلاً regex با alternation بود که هرگز
# handler را capture نمی‌کرد (`[^>]*` با greedy تا `>` پیش می‌رفت و
# سپس شاخه `onClick={...}` همیشه fail می‌کرد چون موقعیت پس از `>` بود).
# اکنون attrs و body جداگانه capture می‌شوند و onClick در attrs جستجو می‌شود.
_UI_BUTTON_RE = re.compile(
    r"<button(?P<attrs>[^>]*)>(?P<body>.*?)</button>",
    re.DOTALL | re.IGNORECASE,
)
_BUTTON_ONCLICK_RE = re.compile(r"onClick\s*=\s*\{([^}]+)\}", re.IGNORECASE)
_BUTTON_DISABLED_RE = re.compile(r"\bdisabled\b", re.IGNORECASE)
_UI_FORM_RE = re.compile(r"<form[^>]*>", re.IGNORECASE)
_UI_INPUT_RE = re.compile(
    r"<input[^>]*(?:type=\{?[\"']?([^\"'}\s]+)[\"']?\}?|name=\{?[\"']?([^\"'}\s]+))",
)
_UI_SELECT_RE = re.compile(r"<[Ss]elect[^>]*>", re.MULTILINE)
_UI_LINK_RE = re.compile(r"<Link[^>]*href=\{?[\"']([^\"'}]+)[\"']", re.MULTILINE)
_UI_MODAL_TRIGGER_RE = re.compile(
    r"set(?:Show|Open|Visible)([A-Z][a-zA-Z0-9]+)\s*\(\s*true",
)


def _extract_ui_elements(
    file_contents: Dict[str, str],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not (path.endswith(".tsx") or path.endswith(".jsx")):
            continue
        content = content[:_MAX_CONTENT_SCAN]

        # buttons
        for m in _UI_BUTTON_RE.finditer(content):
            attrs = (m.group("attrs") or "").strip()
            body_raw = (m.group("body") or "").strip()
            # حذف tags داخلی برای استخراج متن (مثل <span>...</span>)
            label = re.sub(r"<[^>]+>", "", body_raw)[:120].strip()
            # 🆕 (Phase 5 — bug 15) — onClick را در attrs جستجو می‌کنیم
            onclick_m = _BUTTON_ONCLICK_RE.search(attrs)
            handler = (onclick_m.group(1).strip()[:200] if onclick_m else "")
            # 🆕 hand-off form submit ها: button با type="submit" در <form> هم
            # «دارای handler» است (به onSubmit fielding می‌شود).
            is_submit = bool(re.search(r'type\s*=\s*["\']?submit', attrs, re.IGNORECASE))
            # 🆕 disabled ولی با onClick هنوز button فعال است
            has_handler = bool(handler) or is_submit
            out.append({
                "type": "button",
                "label": label,
                "handler": handler,
                "file": path,
                "has_handler": has_handler,
                "is_submit": is_submit,
            })
            if len(out) >= _MAX_ITEMS_PER_LAYER:
                return out
        # forms
        for m in _UI_FORM_RE.finditer(content):
            out.append({"type": "form", "file": path})
        # inputs
        for m in _UI_INPUT_RE.finditer(content):
            itype = (m.group(1) or "text").strip()[:30]
            iname = (m.group(2) or "").strip()[:50]
            out.append({"type": "input", "input_type": itype, "name": iname, "file": path})
        # selects
        for m in _UI_SELECT_RE.finditer(content):
            out.append({"type": "select", "file": path})
        # links
        for m in _UI_LINK_RE.finditer(content):
            href = m.group(1).strip()[:200]
            out.append({"type": "link", "href": href, "file": path})
        # modal triggers
        for m in _UI_MODAL_TRIGGER_RE.finditer(content):
            modal_name = m.group(1)[:50]
            out.append({"type": "modal_trigger", "modal_name": modal_name, "file": path})

        if len(out) >= _MAX_ITEMS_PER_LAYER:
            return out
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 4: DB schema
# ─────────────────────────────────────────────────────────────────────────

_DATACLASS_RE = re.compile(r"@dataclass\s*\n+class\s+([A-Z][a-zA-Z0-9_]*)\s*[:(]", re.MULTILINE)
_COLUMN_RE = re.compile(r"(\w+)\s*=\s*Column\s*\(\s*([A-Za-z]+)", re.MULTILINE)
_MIGRATION_RE = re.compile(r"^(?:def\s+upgrade|def\s+downgrade|alembic|migrate)", re.MULTILINE)


def _extract_db_schema(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        content = content[:_MAX_CONTENT_SCAN]
        # dataclasses (می‌تواند DB-relevant باشد)
        for m in _DATACLASS_RE.finditer(content):
            cls_name = m.group(1)
            # extract fields نزدیک کلاس
            cls_pos = m.end()
            cls_block = content[cls_pos:cls_pos + 3000]
            # field lines: "    name: type = default"
            fields = re.findall(
                r"^\s+([a-z_][a-z0-9_]*)\s*:\s*([A-Za-z][A-Za-z0-9_\[\],\s\.\"']+)(?:\s*=\s*(.+?))?$",
                cls_block, re.MULTILINE,
            )
            out.append({
                "kind": "dataclass",
                "name": cls_name,
                "file": path,
                "field_count": len(fields),
                "fields": [{"name": f[0], "type": f[1][:80].strip()} for f in fields[:30]],
            })
        # SQLAlchemy columns
        for m in _COLUMN_RE.finditer(content):
            col_name = m.group(1)
            col_type = m.group(2)
            out.append({
                "kind": "column",
                "name": col_name,
                "type": col_type,
                "file": path,
            })
        # migrations
        if _MIGRATION_RE.search(content) and "migration" in path.lower():
            out.append({"kind": "migration", "file": path})

        if len(out) >= _MAX_ITEMS_PER_LAYER:
            break
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 5: Env vars
# ─────────────────────────────────────────────────────────────────────────

_PY_ENV_RE = re.compile(
    r"os\.environ\.get\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']"
    r"|os\.getenv\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']"
    r"|os\.environ\[\s*[\"']([A-Z_][A-Z0-9_]*)[\"']\s*\]",
)
_JS_ENV_RE = re.compile(r"process\.env\.([A-Z_][A-Z0-9_]*)")


def _extract_env_vars(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    var_to_files: Dict[str, Set[str]] = {}
    for path, content in file_contents.items():
        content = content[:_MAX_CONTENT_SCAN]
        if path.endswith(".py"):
            for m in _PY_ENV_RE.finditer(content):
                name = m.group(1) or m.group(2) or m.group(3)
                if name:
                    var_to_files.setdefault(name, set()).add(path)
        elif path.endswith((".ts", ".tsx", ".js", ".jsx")):
            for m in _JS_ENV_RE.finditer(content):
                name = m.group(1)
                var_to_files.setdefault(name, set()).add(path)
    return [
        {"name": name, "used_in_files": sorted(files)[:10], "usage_count": len(files)}
        for name, files in sorted(var_to_files.items())
    ][:_MAX_ITEMS_PER_LAYER]


# ─────────────────────────────────────────────────────────────────────────
# Layer 6: Config files
# ─────────────────────────────────────────────────────────────────────────

_CONFIG_EXTS = (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")


def _extract_config_files(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path in sorted(file_contents.keys()):
        low = path.lower()
        if (
            low.endswith(_CONFIG_EXTS)
            or low.endswith(".env")
            or "/.env." in low
            or low.endswith(".env.example")
        ):
            content = file_contents[path][:5000]
            line_count = content.count("\n")
            out.append({
                "file": path,
                "size_bytes": len(file_contents[path]),
                "line_count": line_count,
            })
    return out[:_MAX_ITEMS_PER_LAYER]


# ─────────────────────────────────────────────────────────────────────────
# Layer 7: Dependencies
# ─────────────────────────────────────────────────────────────────────────

def _extract_dependencies(file_contents: Dict[str, str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"python": [], "node": []}
    for path, content in file_contents.items():
        path_low = path.lower().replace("\\", "/")
        # requirements*.txt anywhere
        if path_low.endswith("requirements.txt") or "requirements" in path_low.rsplit("/", 1)[-1]:
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    pkg = re.split(r"[=<>!~\s;\[]", line, 1)[0].strip()
                    if pkg and re.match(r"^[a-zA-Z0-9._-]+$", pkg):
                        out["python"].append(pkg)
        # pyproject.toml dependencies block
        elif path_low.endswith("pyproject.toml"):
            for m in re.finditer(r'^\s*"([a-zA-Z0-9._-]+)\s*[=<>!~]', content, re.MULTILINE):
                out["python"].append(m.group(1))
        elif path_low.endswith("package.json"):
            try:
                import json
                pkg = json.loads(content)
                for sec in ("dependencies", "devDependencies"):
                    for dep_name in (pkg.get(sec) or {}).keys():
                        out["node"].append(dep_name)
            except Exception:
                pass
    out["python"] = sorted(set(out["python"]))[:_MAX_ITEMS_PER_LAYER]
    out["node"] = sorted(set(out["node"]))[:_MAX_ITEMS_PER_LAYER]
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 8: Scripts
# ─────────────────────────────────────────────────────────────────────────

def _extract_scripts(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        # shell scripts
        if path.endswith(".sh") or content.startswith("#!/"):
            out.append({"kind": "shell", "file": path, "size": len(content)})
        # package.json scripts
        elif path.endswith("package.json"):
            try:
                import json
                pkg = json.loads(content)
                for name, cmd in (pkg.get("scripts") or {}).items():
                    out.append({
                        "kind": "npm_script", "name": name,
                        "cmd": str(cmd)[:200], "file": path,
                    })
            except Exception:
                pass
        # pyproject.toml scripts
        elif path.endswith("pyproject.toml"):
            for m in re.finditer(
                r'^(\w+)\s*=\s*"([^"]+)"', content[:_MAX_CONTENT_SCAN], re.MULTILINE,
            ):
                if "scripts" in content[:m.start()][-200:].lower():
                    out.append({
                        "kind": "py_script", "name": m.group(1),
                        "cmd": m.group(2)[:200], "file": path,
                    })
    return out[:_MAX_ITEMS_PER_LAYER]


# ─────────────────────────────────────────────────────────────────────────
# Layer 9: Cron / scheduled
# ─────────────────────────────────────────────────────────────────────────

_SCHEDULER_RE = re.compile(
    r"(apscheduler|BackgroundScheduler|AsyncIOScheduler|"
    r"scheduler\.add_job|"
    r"BackgroundTasks?\(|"
    r"asyncio\.create_task\(\s*([a-zA-Z_][a-zA-Z0-9_]*)|"
    r"@scheduler\.scheduled_job)",
)


def _extract_scheduled(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        content = content[:_MAX_CONTENT_SCAN]
        for m in _SCHEDULER_RE.finditer(content):
            kind = m.group(1) or m.group(0)
            target = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            out.append({
                "kind": kind[:50],
                "target": target,
                "file": path,
                "line": content[:m.start()].count("\n") + 1,
            })
            if len(out) >= _MAX_ITEMS_PER_LAYER:
                return out
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 10: Routes
# ─────────────────────────────────────────────────────────────────────────

def _extract_routes(file_contents: Dict[str, str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"frontend": [], "backend": []}
    for path in file_contents.keys():
        # Next.js app router
        m = re.match(r"frontend/src/app/(.+?)/page\.(tsx|jsx|ts|js)$", path)
        if m:
            route = "/" + m.group(1).replace("[", ":").replace("]", "")
            out["frontend"].append(route)
        # Pages router fallback
        m2 = re.match(r"frontend/src/pages/(.+?)\.(tsx|jsx|ts|js)$", path)
        if m2:
            route = "/" + m2.group(1).rstrip("/index")
            out["frontend"].append(route)
    # backend از layer 2 endpoints جدا
    out["frontend"] = sorted(set(out["frontend"]))[:_MAX_ITEMS_PER_LAYER]
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 11: Notification calls (R12)
# ─────────────────────────────────────────────────────────────────────────

_NOTIFY_RE = re.compile(
    r"(notify_event|send_telegram|bot\.send_message|"
    r"send_message|notification_service\.|"
    r"telegram_compose\.)\s*\(",
)


def _extract_notifications(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not path.endswith(".py"):
            continue
        content = content[:_MAX_CONTENT_SCAN]
        for m in _NOTIFY_RE.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            call_name = m.group(1).strip()
            # extract context (200 chars بعد از match)
            ctx = content[m.start():m.start() + 600]
            # silent flag
            silent_m = re.search(r"silent\s*=\s*(True|False)", ctx)
            silent_val = silent_m.group(1) if silent_m else None
            # event_type if present
            event_m = re.search(r"event[_\"']?\s*[:=]\s*[\"']([^\"']+)[\"']", ctx)
            event_type = event_m.group(1) if event_m else None
            out.append({
                "call": call_name,
                "file": path,
                "line": line_no,
                "event_type": event_type,
                "silent_default": silent_val,
                "context_snippet": ctx[:200].replace("\n", " "),
            })
            if len(out) >= _MAX_ITEMS_PER_LAYER:
                return out
    return out


# ─────────────────────────────────────────────────────────────────────────
# Layer 12: UI options/settings (R8)
# ─────────────────────────────────────────────────────────────────────────

_UI_CHECKBOX_RE = re.compile(
    r"<input[^>]*type=[\"']checkbox[\"'][^>]*"
    r"(?:checked=\{([^}]*)\}|onChange=\{([^}]*)\})",
    re.DOTALL,
)
_UI_SLIDER_RE = re.compile(
    r"<input[^>]*type=[\"']range[\"'][^>]*"
    r"(?:value=\{([^}]*)\}|onChange=\{([^}]*)\})",
    re.DOTALL,
)
_UI_DROPDOWN_RE = re.compile(
    r"<select[^>]*"
    r"(?:value=\{([^}]*)\}|onChange=\{([^}]*)\})",
    re.DOTALL | re.IGNORECASE,
)


# 🆕 (Phase 5 — bug 17) — کلمات رزرو که نباید به‌عنوان field_hint
# گرفته شوند (پارامترهای callback، نام‌های frameworks، utility ها).
_FIELD_HINT_DENY = {
    "e", "event", "evt", "ev", "ev_", "_e",
    "el", "elem", "element",
    "v", "val", "value", "val_",
    "i", "idx", "index", "n",
    "x", "y", "z",
    "t", "data", "item", "items", "row", "col",
    "key", "id", "type", "name", "props",
    "ref", "state", "set", "get", "fn", "cb",
    "true", "false", "null", "undefined",
    "react", "default", "const", "let", "var",
}


def _smart_field_hint(ctx: str) -> Optional[str]:
    """field name واقعی را از context استخراج کن.

    استراتژی:
      ۱) `name="xyz"` یا `id="xyz"` در attrs
      ۲) `checked={state.xyz}` یا `value={xyz}` — متغیر state
      ۳) `onChange={(e) => setXyz(e.target...)` — setter name → xyz
      ۴) اولین identifier معنادار که در _FIELD_HINT_DENY نباشد.
    """
    # ۱) name="..." یا id="..."
    m = re.search(r'(?:name|id)\s*=\s*["\']([a-zA-Z][a-zA-Z0-9_]{2,})["\']', ctx)
    if m:
        return m.group(1)
    # ۲) setXyz(...) → state name
    m = re.search(r'\bset([A-Z][a-zA-Z0-9_]{1,})\s*\(', ctx)
    if m:
        nm = m.group(1)
        return nm[0].lower() + nm[1:]  # camelCase
    # ۳) checked={state.xyz} | value={xyz}
    m = re.search(r'(?:checked|value)\s*=\s*\{[^.}]*?\.([a-z_][a-zA-Z0-9_]{2,})', ctx)
    if m and m.group(1).lower() not in _FIELD_HINT_DENY:
        return m.group(1)
    m = re.search(r'(?:checked|value)\s*=\s*\{([a-z_][a-zA-Z0-9_]{2,})', ctx)
    if m and m.group(1).lower() not in _FIELD_HINT_DENY:
        return m.group(1)
    # ۴) fallback: اولین identifier معنادار
    for cand in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', ctx):
        if cand.lower() not in _FIELD_HINT_DENY:
            return cand
    return None


def _extract_ui_options(file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, content in file_contents.items():
        if not (path.endswith(".tsx") or path.endswith(".jsx")):
            continue
        content = content[:_MAX_CONTENT_SCAN]
        # checkboxes
        for m in _UI_CHECKBOX_RE.finditer(content):
            ctx = (m.group(1) or m.group(2) or "")[:200]
            field = _smart_field_hint(ctx)
            out.append({
                "type": "checkbox", "file": path,
                "field_hint": field, "context": ctx,
            })
        # sliders
        for m in _UI_SLIDER_RE.finditer(content):
            ctx = (m.group(1) or m.group(2) or "")[:200]
            field = _smart_field_hint(ctx)
            out.append({
                "type": "slider", "file": path,
                "field_hint": field, "context": ctx,
            })
        # dropdowns (selects with onChange)
        for m in _UI_DROPDOWN_RE.finditer(content):
            ctx = (m.group(1) or m.group(2) or "")[:200]
            field = _smart_field_hint(ctx)
            out.append({
                "type": "dropdown", "file": path,
                "field_hint": field, "context": ctx,
            })
        if len(out) >= _MAX_ITEMS_PER_LAYER:
            return out
    return out


# ─────────────────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────────────────

def build_inventory(
    file_contents: Dict[str, str],
    all_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """ساخت inventory کامل از همه ۱۲ لایه.

    Args:
        file_contents: {file_path: content} از scan service
        all_paths: لیست همه paths (شاید paths که content fetched نشده)

    Returns:
        dict شامل ۱۲ کلید (یکی برای هر لایه) + meta.
        هر لایه fail-soft است.
    """
    paths = all_paths or list(file_contents.keys())
    inventory: Dict[str, Any] = {
        "_meta": {
            "total_files_in_repo": len(paths),
            "files_with_content": len(file_contents),
            "max_items_per_layer": _MAX_ITEMS_PER_LAYER,
        },
        "files": paths[:_MAX_ITEMS_PER_LAYER * 4],  # همه paths (تا 2000)
    }

    layer_fns: List[Tuple[str, Any]] = [
        ("backend_endpoints", _extract_backend_endpoints),
        ("ui_elements", _extract_ui_elements),
        ("db_schema", _extract_db_schema),
        ("env_vars", _extract_env_vars),
        ("config_files", _extract_config_files),
        ("dependencies", _extract_dependencies),
        ("scripts", _extract_scripts),
        ("scheduled", _extract_scheduled),
        ("routes", _extract_routes),
        ("notification_calls", _extract_notifications),
        ("ui_options", _extract_ui_options),
    ]
    for layer_name, fn in layer_fns:
        try:
            inventory[layer_name] = fn(file_contents)
        except Exception as e:
            logger.warning(f"inventory: layer {layer_name} failed: {e}")
            inventory[layer_name] = []
            inventory["_meta"].setdefault("failed_layers", []).append(layer_name)

    # counts برای دسترسی سریع
    inventory["_meta"]["counts"] = {
        k: (
            sum(len(v) for v in val.values())
            if isinstance(val, dict) and all(isinstance(v, list) for v in val.values())
            else (len(val) if isinstance(val, list) else 0)
        )
        for k, val in inventory.items()
        if not k.startswith("_") and k != "files"
    }
    inventory["_meta"]["counts"]["files"] = len(inventory["files"])
    return inventory
