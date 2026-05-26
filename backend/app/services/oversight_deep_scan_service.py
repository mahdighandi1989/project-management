"""
Deep Scan Service
=================
موتور اسکن عمیق پروژه‌های گیت‌هاب. به‌صورت چند فازی:
  1) بارگذاری ساختار کامل (recursive)
  2) دسته‌بندی فایل‌ها و شناسایی stack
  3) انتخاب هوشمند فایل‌های کلیدی + خواندن کامل آن‌ها
  4) تحلیل چندبُعدی (Pass A..H) — هر pass یک system prompt تخصصی
  5) تجمیع، dedup، اولویت‌بندی → ساخت تسک با پرامپت قوی
  6) progress زنده در فایل JSON قابل polling
"""

from __future__ import annotations

import os
import re
import json
import uuid
import base64
import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# مسیرها
from .oversight_service import (
    STORAGE_DIR,
    get_oversight_service,
    OversightTask,
    now_iso,
    _write_json,
    _read_json,
    get_github_token,
)
from .oversight_strong_prompt import build_strong_prompt

STRUCTURE_DIR = STORAGE_DIR / "structure"


# (audit fix I3) — sentinel exception برای skip post-scan side-effects
# (notification + PDF bundle + scan_v5 archive) در حالت Inspector scan موردی.
# این subclass از Exception است، پس توسط `except Exception` کلی catch می‌شود.
class _InspectorSkipPostScan(Exception):
    pass
PROGRESS_DIR = STORAGE_DIR / "scan_progress"
SCAN_RESULTS_DIR = STORAGE_DIR / "scan_results"
for d in (STRUCTURE_DIR, PROGRESS_DIR, SCAN_RESULTS_DIR):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


# =====================================================================
# نوع و دسته‌بندی فایل‌ها
# =====================================================================

FILE_KIND_RULES: List[Tuple[str, str]] = [
    # (regex on path, kind)
    (r"(?:^|/)__tests?__/|\.test\.|\.spec\.|/tests?/", "test"),
    (r"(?:^|/)migrations?/", "migration"),
    (r"(?:^|/)(?:docs?|documentation)/", "docs"),
    (r"\.md$|\.mdx$|README|CHANGELOG", "docs"),
    (r"(?:^|/)(?:scripts?|tools?)/", "script"),
    (r"\.(ya?ml|toml|ini|cfg|conf)$|^\.env|Dockerfile|docker-compose", "config"),
    (r"(?:^|/)pages?/|/app/.+/page\.(tsx|jsx|ts|js)$", "page"),
    (r"(?:^|/)routes?/|/api/", "route"),
    (r"(?:^|/)components?/", "component"),
    (r"(?:^|/)services?/", "service"),
    (r"(?:^|/)models?/", "model"),
    (r"(?:^|/)middlewares?/", "middleware"),
    (r"(?:^|/)hooks?/", "hook"),
    (r"(?:^|/)utils?/|(?:^|/)helpers?/|(?:^|/)lib/", "util"),
    (r"(?:^|/)types?/|\.d\.ts$", "types"),
]

ENTRY_POINTS = {
    "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
    "server.js", "index.js", "app.js",
    "page.tsx", "layout.tsx", "_app.tsx", "_document.tsx",
    "index.html", "index.tsx", "main.tsx", "App.tsx",
}

DEPENDENCY_FILES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "Pipfile", "Pipfile.lock", "pyproject.toml", "poetry.lock",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
    "Gemfile", "Gemfile.lock",
    "composer.json", "composer.lock",
    "pom.xml", "build.gradle",
}


def _classify_file(path: str) -> str:
    """تعیین نوع فایل بر اساس مسیر آن."""
    name = path.split("/")[-1]
    if name in DEPENDENCY_FILES:
        return "dependency"
    if name in ENTRY_POINTS:
        return "entry"
    for pattern, kind in FILE_KIND_RULES:
        if re.search(pattern, path):
            return kind
    return "other"


def _detect_stack(paths: List[str], dependency_contents: Dict[str, str]) -> List[str]:
    """تشخیص stack بر اساس فایل‌ها و وابستگی‌ها."""
    stack = set()
    pkg_json = dependency_contents.get("package.json", "")
    if pkg_json:
        if "next" in pkg_json:
            stack.add("nextjs")
        if "react" in pkg_json and "next" not in pkg_json:
            stack.add("react")
        if "vue" in pkg_json:
            stack.add("vue")
        if "express" in pkg_json:
            stack.add("express")
        if "@nestjs" in pkg_json:
            stack.add("nestjs")
        if "vite" in pkg_json:
            stack.add("vite")
    req_txt = dependency_contents.get("requirements.txt", "") + dependency_contents.get(
        "pyproject.toml", ""
    )
    if req_txt:
        low = req_txt.lower()
        if "fastapi" in low:
            stack.add("fastapi")
        if "django" in low:
            stack.add("django")
        if "flask" in low:
            stack.add("flask")
    if "go.mod" in dependency_contents:
        stack.add("go")
    if "Cargo.toml" in dependency_contents:
        stack.add("rust")
    if "Gemfile" in dependency_contents:
        stack.add("rails")
    if "pom.xml" in dependency_contents:
        stack.add("java")
    return sorted(stack)


# =====================================================================
# Progress
# =====================================================================

def _progress_path(watched_id: str) -> Path:
    return PROGRESS_DIR / f"{watched_id}.json"


def write_progress(watched_id: str, **fields: Any) -> None:
    """به‌روزرسانی فایل پیشرفت اسکن."""
    path = _progress_path(watched_id)
    current = _read_json(path, {}) or {}
    current.update(fields)
    current["updated_at"] = now_iso()
    _write_json(path, current)


def read_progress(watched_id: str) -> Dict[str, Any]:
    return _read_json(_progress_path(watched_id), {}) or {}


# =====================================================================
# GitHub helpers
# =====================================================================

def _gh_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-creator-deep-scan/1.0",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }


async def _gh_get_json(session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> Any:
    try:
        async with session.get(url, headers=headers, timeout=30) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


async def _fetch_file_content(
    session: aiohttp.ClientSession,
    repo: str,
    path: str,
    headers: Dict[str, str],
    branch: Optional[str] = None,
    max_bytes: int = 60000,
) -> Optional[str]:
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    if branch:
        url += f"?ref={branch}"
    data = await _gh_get_json(session, url, headers)
    if not data or not isinstance(data, dict):
        return None
    if data.get("type") != "file" or not data.get("content"):
        return None
    try:
        decoded = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return None
    if len(decoded) > max_bytes:
        # 🆕 (Phase 5 — bug 24) — قبل از truncate، همهٔ import ها را از full
        # content استخراج می‌کنیم و در انتها append می‌کنیم. علت: فایل‌های
        # بزرگ مثل oversight_deep_scan_service.py (۸۸KB) local imports عمیق
        # درون توابع دارند که بدون این کار از import graph می‌افتند و
        # ماژول‌های هدف false-positive «unused_file» می‌گیرند.
        try:
            _is_py = path.endswith(".py")
            _is_js = path.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"))
            _imports_block: List[str] = []
            if _is_py:
                for _m in re.finditer(
                    r"^\s*(?:from\s+[\.\w]+\s+import\s+[^\n]+|import\s+[\w\.,\s]+)",
                    decoded, re.MULTILINE,
                ):
                    _line = _m.group(0).strip()
                    if _line and len(_line) < 500:
                        _imports_block.append(_line)
            elif _is_js:
                for _m in re.finditer(
                    r"""^\s*(?:import\s+[^\n]+?\bfrom\s+['"][^'"]+['"]|import\s+['"][^'"]+['"]|(?:const|let|var)\s+[^=]+=\s*require\(\s*['"][^'"]+['"]\s*\))""",
                    decoded, re.MULTILINE,
                ):
                    _line = _m.group(0).strip()
                    if _line and len(_line) < 500:
                        _imports_block.append(_line)
            decoded = decoded[:max_bytes] + "\n... [TRUNCATED]"
            if _imports_block:
                # حذف duplicate ها با حفظ ترتیب
                _seen: set = set()
                _uniq: List[str] = []
                for _il in _imports_block:
                    if _il not in _seen:
                        _seen.add(_il)
                        _uniq.append(_il)
                decoded += "\n\n# [IMPORTS_RECOVERED_FROM_FULL_FILE]\n" + "\n".join(_uniq)
        except Exception:
            # هرگز fetch نباید fail-soft نکند
            decoded = decoded[:max_bytes] + "\n... [TRUNCATED]"
    return decoded


# =====================================================================
# File scoring (Phase 2)
# =====================================================================

# =====================================================================
# Import graph (Phase 2.5) — parse Python/JS/TS imports to build a real
# dependency map. Used both to (a) score files (hubs ranked higher) and
# (b) enrich each finding with `related_files` so external tools know
# which neighbours to also inspect.
# =====================================================================

_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(\.+[\w\.]*|[\w\.]+)\s+import|import\s+([\w\.]+))",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"\n]+?\s+from\s+)?["']([^"']+)["']|require\(\s*["']([^"']+)["']\s*\))""",
    re.MULTILINE,
)


def _resolve_py_import(module: str, all_paths: List[str]) -> Optional[str]:
    """تبدیل `app.services.foo` → `backend/app/services/foo.py` (best-effort)."""
    if not module:
        return None
    parts = module.split(".")
    candidates = [
        "/".join(parts) + ".py",
        "/".join(parts) + "/__init__.py",
        parts[-1] + ".py",
    ]
    for c in candidates:
        for p in all_paths:
            if p.endswith("/" + c) or p == c:
                return p
    return None


# 🆕 (Phase 5 — bug 14) — relative imports باید resolve شوند
# (`from .api.routes import xxx` در `backend/app/main.py` ⇒
# `backend/app/api/routes/xxx.py`). در غیر این صورت همه فایل‌ها
# false-positive «unused_file» می‌گیرند.
def _resolve_py_relative_import(
    module_or_dots: str,
    imported_names: List[str],
    importer_path: str,
    all_paths: List[str],
) -> List[str]:
    """resolve `from .a.b import x, y` به مسیرهای فایل.

    `module_or_dots` می‌تواند `.`, `..`, `.a`, `..a.b` باشد.
    `imported_names` نام‌های `import (x, y, z)` — هر کدام ممکن است
    خودش یک sub-module باشد.
    Returns: لیست paths که resolve شدند.
    """
    if not module_or_dots.startswith("."):
        return []
    # شمارش dots
    dots = 0
    rest = module_or_dots
    while rest.startswith("."):
        dots += 1
        rest = rest[1:]
    # importer_path → directory parts
    dir_parts = importer_path.split("/")[:-1]  # حذف نام فایل
    # هر dot اضافه = یک level بالاتر (اولین dot = same package)
    if dots > 1:
        dir_parts = dir_parts[: len(dir_parts) - (dots - 1)]
    if rest:
        dir_parts = dir_parts + rest.split(".")
    base = "/".join(dir_parts)
    resolved: List[str] = []
    # حالت ۱: خود base یک ماژول است (یا یک سری نام در آن import شده)
    candidates = [base + ".py", base + "/__init__.py"]
    for c in candidates:
        if c in all_paths:
            resolved.append(c)
    # حالت ۲: نام‌های import شده ممکن است sub-modules باشند
    for nm in imported_names:
        nm_clean = nm.strip().split(" as ")[0].strip()
        if not nm_clean or nm_clean == "*":
            continue
        sub_candidates = [
            base + "/" + nm_clean + ".py",
            base + "/" + nm_clean + "/__init__.py",
        ]
        for c in sub_candidates:
            if c in all_paths:
                resolved.append(c)
    return resolved


# regex برای استخراج نام‌های `import (a, b, c)` در کنار `from X import ...`
_PY_FROM_IMPORT_NAMES_RE = re.compile(
    r"^\s*from\s+(\.+[\w\.]*|[\w\.]+)\s+import\s+([^\n]+?)(?:\n|$)",
    re.MULTILINE,
)


def _resolve_js_import(spec: str, importer_path: str, all_paths: List[str]) -> Optional[str]:
    """تبدیل import نسبی (./X, ../Y) به مسیر کامل پروژه."""
    if not spec or spec.startswith(("http://", "https://")):
        return None
    if not (spec.startswith(".") or spec.startswith("/")):
        return None  # bare module (npm package) — out of scope
    base = "/".join(importer_path.split("/")[:-1])
    parts = (base + "/" + spec).split("/") if not spec.startswith("/") else spec.split("/")
    stack: List[str] = []
    for seg in parts:
        if seg in ("", "."):
            continue
        if seg == "..":
            if stack:
                stack.pop()
            continue
        stack.append(seg)
    target = "/".join(stack)
    exts = ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", "/index.ts", "/index.tsx", "/index.js", "/index.jsx")
    for e in exts:
        cand = target + e
        if cand in all_paths:
            return cand
    return None


def _build_import_graph(
    deep_contents: Dict[str, str], all_paths: List[str]
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, int]]:
    """ساخت گراف وابستگی از فایل‌های deep-read شده.

    خروجی:
      imports[file] -> List[file]   فایل‌هایی که file آنها را import می‌کند
      imported_by[file] -> List[file]   فایل‌هایی که file را import می‌کنند
      import_counts[file] -> int         تعداد imported_by (برای scoring)
    """
    imports: Dict[str, List[str]] = {}
    imported_by: Dict[str, List[str]] = {}
    path_set = set(all_paths)

    for fpath, content in deep_contents.items():
        if not content:
            continue
        deps: List[str] = []
        if fpath.endswith(".py"):
            # 🆕 (Phase 5 — bug 14) — relative imports اکنون resolve می‌شوند
            # (قبلاً silently skip می‌شد → همه فایل‌های دارای imported_by صرفاً
            # از relative، false-positive «unused_file» می‌گرفتند).
            for m in _PY_FROM_IMPORT_NAMES_RE.finditer(content):
                mod = (m.group(1) or "").strip()
                names_raw = (m.group(2) or "").strip()
                # پاک‌سازی parentheses و trailing comments
                names_raw = names_raw.split("#")[0].strip()
                if names_raw.startswith("("):
                    # ممکن است multi-line باشد — بهترین تلاش
                    names_raw = names_raw.lstrip("(").rstrip(")").strip()
                names = [n.strip() for n in names_raw.split(",") if n.strip()]
                if mod.startswith("."):
                    for r in _resolve_py_relative_import(mod, names, fpath, list(path_set)):
                        if r and r != fpath:
                            deps.append(r)
                else:
                    resolved = _resolve_py_import(mod, list(path_set))
                    if resolved and resolved != fpath:
                        deps.append(resolved)
                    # هر name هم ممکن است sub-module باشد (مثل
                    # `from app.api.routes import a, b, c` → a.py, b.py, c.py)
                    for nm in names:
                        nm = nm.split(" as ")[0].strip()
                        if not nm or nm == "*":
                            continue
                        sub_resolved = _resolve_py_import(mod + "." + nm, list(path_set))
                        if sub_resolved and sub_resolved != fpath:
                            deps.append(sub_resolved)
            # `import x.y.z` ها هم همچنان handle شوند
            for m in _PY_IMPORT_RE.finditer(content):
                mod = m.group(2) or ""
                if not mod or mod.startswith("."):
                    continue
                resolved = _resolve_py_import(mod, list(path_set))
                if resolved and resolved != fpath:
                    deps.append(resolved)
        elif fpath.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
            for m in _JS_IMPORT_RE.finditer(content):
                spec = m.group(1) or m.group(2) or ""
                resolved = _resolve_js_import(spec, fpath, list(path_set))
                if resolved and resolved != fpath:
                    deps.append(resolved)
        # dedup
        deps = list(dict.fromkeys(deps))
        if deps:
            imports[fpath] = deps
            for d in deps:
                imported_by.setdefault(d, []).append(fpath)

    import_counts = {k: len(v) for k, v in imported_by.items()}
    return imports, imported_by, import_counts


def _related_for_paths(
    paths: List[str],
    imports: Dict[str, List[str]],
    imported_by: Dict[str, List[str]],
    limit: int = 6,
) -> List[Dict[str, str]]:
    """برای یک یا چند فایل هدف، لیست فایل‌های مرتبط (importer/importee) برمی‌گرداند."""
    out: List[Dict[str, str]] = []
    seen: set = set()
    for p in paths:
        for dep in imports.get(p, [])[:4]:
            if dep in seen:
                continue
            seen.add(dep)
            out.append({"path": dep, "reason": f"`{p.split('/')[-1]}` این فایل را import می‌کند"})
        for dep in imported_by.get(p, [])[:4]:
            if dep in seen:
                continue
            seen.add(dep)
            out.append({"path": dep, "reason": f"این فایل `{p.split('/')[-1]}` را import می‌کند (caller)"})
        if len(out) >= limit:
            break
    return out[:limit]


def _extract_idea_keywords(idea: str, max_keywords: int = 15) -> List[str]:
    """🆕 استخراج کلمات کلیدی از idea کاربر برای keyword-aware ranking.

    - CamelCase identifiers (مثل OversightPanel)
    - snake_case identifiers (مثل copy_prompt)
    - کلمات فارسی 4+ کاراکتر
    - کلمات انگلیسی 4+ کاراکتر (با حذف stopwords)
    """
    if not idea:
        return []
    import re
    text = idea.strip()
    keywords: set = set()
    # CamelCase
    for m in re.findall(r"\b[A-Z][a-zA-Z0-9]{3,}\b", text):
        keywords.add(m.lower())
    # snake_case طولانی
    for m in re.findall(r"\b[a-z][a-z0-9_]{4,}\b", text):
        keywords.add(m)
    # کلمات فارسی
    for m in re.findall(r"[؀-ۿ]{4,}", text):
        keywords.add(m)
    # کلمات انگلیسی معمول (4+ char)
    for m in re.findall(r"\b[a-zA-Z]{4,}\b", text):
        keywords.add(m.lower())
    # حذف stopwords
    stopwords = {
        "function", "method", "class", "import", "should", "would",
        "this", "that", "these", "those", "with", "from", "into",
        "make", "want", "need", "have", "more", "less", "some", "many",
        "است", "این", "آن", "های", "هایی", "می‌شود", "شده", "باشد",
        "برای", "وجود", "ندارد", "دارد", "کاربر", "بتواند", "خواهد",
    }
    keywords = {k for k in keywords if k.lower() not in stopwords and len(k) >= 4}
    # sort by length descending — long keywords are more specific
    return sorted(keywords, key=lambda x: -len(x))[:max_keywords]


def _score_files(
    paths: List[str],
    sizes: Dict[str, int],
    recent_changed_files: List[str],
    import_counts: Dict[str, int],
    idea_keywords: Optional[List[str]] = None,  # 🆕 برای keyword-aware boost
) -> List[Tuple[str, int]]:
    """ترتیب فایل‌ها بر اساس امتیاز اهمیت برای deep-read."""
    scores: Dict[str, int] = {}
    kws = [k.lower() for k in (idea_keywords or []) if k]
    for p in paths:
        s = 0
        name = p.split("/")[-1]
        if name in ENTRY_POINTS:
            s += 10
        kind = _classify_file(p)
        if kind in ("page", "route"):
            s += 8
        elif kind in ("component", "service", "model", "middleware", "hook"):
            s += 4
        elif kind in ("config", "util"):
            s += 2
        elif kind == "test":
            s += 1
        if p in recent_changed_files:
            s += 4
        # هاب‌ها
        if import_counts.get(p, 0) >= 5:
            s += min(import_counts[p], 6)
        # critical paths
        if any(seg in p for seg in ("/api/", "/auth/", "/security", "/middleware")):
            s += 3
        # حجم بزرگ
        sz = sizes.get(p, 0)
        if sz > 20000:
            s += 2
        # 🆕 keyword-aware boost: اگر path شامل کلمات کلیدی idea است
        # هر keyword match = +5 score (شاخص قوی برای relevance)
        if kws:
            p_low = p.lower()
            matched_kws = sum(1 for kw in kws if kw in p_low)
            if matched_kws > 0:
                s += matched_kws * 5
                # bonus اگر در نام فایل (basename) match بود — قوی‌تر
                name_low = name.lower()
                if any(kw in name_low for kw in kws):
                    s += 3
        scores[p] = s
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# =====================================================================
# Multi-pass AI analysis
# =====================================================================

PASSES = [
    ("frontend", "تحلیل صفحات و کامپوننت‌های Frontend"),
    ("backend", "تحلیل Routes و Endpointهای Backend"),
    ("cross_stack", "سازگاری Frontend ↔ Backend"),
    ("security", "آسیب‌پذیری‌های امنیتی"),
    ("integrity", "یکپارچگی Cross-cutting و conflictها"),
    ("quality", "کیفیت کد و dead code"),
    ("dependency", "ناسازگاری‌های runtime و dependency"),
    ("completeness", "کامل بودن نسبت به هدف کاربر"),
    # 🆕 Pass I — اسکن امنیتی عمیق با خروجی ساختاریافته
    # (مهاجرت از /projects/[id]/health/security)
    ("security_deep", "اسکن امنیتی عمیق: secrets + license + dependencies"),
    # 🆕 Pass J — تحلیل پوشش تست
    # (مهاجرت از /projects/[id]/health/coverage)
    ("coverage", "تحلیل پوشش تست — فایل‌های untested و gap detection"),
    # 🆕 (P3) Pass K — همراستایی منطقی فایل‌ها/قابلیت‌ها
    ("logical_alignment", "همراستایی منطقی فایل‌ها/قابلیت‌ها + UI binding + conflict detection"),
    # 🆕 (P3) Pass L — صحت رفتاری per-feature
    ("functional_correctness", "صحت رفتاری: edge cases، error handling، runtime errors"),
]


# 🆕 (inspector-scoped-scan) — keyword→passes mapping for narrowing the
# auto-scan when triggered from Inspector chat. Goal: when user asks about a
# specific area (frontend bug, deploy issue, ...), don't run all 12 passes
# and generate 96 unrelated proposals — run only what's relevant.
_INSPECTOR_PASS_KEYWORDS_FA: Dict[str, List[str]] = {
    "frontend": [
        "فرانت", "فرانت‌اند", "صفحه", "کامپوننت", "ui", "تب", "دکمه",
        "نمایش", "رندر", "css", "استایل", "react", "vue", "next",
        "page", "component", "screen",
    ],
    "backend": [
        "بک‌اند", "بک اند", "بک‌اند", "api", "endpoint", "روت", "route",
        "سرور", "fastapi", "django", "flask", "database", "دیتابیس",
        "مدل", "model",
    ],
    "cross_stack": [
        "اتصال", "وصل", "ارتباط", "api call", "fetch", "axios",
        "frontend به backend", "endpoint",
    ],
    "security": ["امنیت", "auth", "احراز هویت", "permission", "vuln", "csrf", "xss"],
    "security_deep": ["secret", "credential", "token", "نشت", "leak", "license"],
    "quality": ["کیفیت", "dead code", "lint", "tidy", "refactor عمومی"],
    "dependency": [
        "deploy", "دیپلوی", "build", "بیلد", "render", "vercel",
        "requirements", "package", "npm", "pip", "dependency", "وابستگی",
        "نصب", "install", "اجرا نشد", "بالا نمیاد", "بالا بیار",
    ],
    "completeness": ["ناقص", "کامل نیست", "todo", "placeholder", "هنوز ساخته نشده"],
    "coverage": ["test", "تست", "coverage", "پوشش تست"],
    "logical_alignment": ["منطق", "logic", "هماهنگی", "conflict", "تضاد"],
    "functional_correctness": [
        "خطا", "error", "باگ", "bug", "کرش", "crash", "ناقص کار",
        "اشتباه", "wrong", "broken", "نشد", "کار نمی‌کند", "کار نمیکنه",
    ],
    "integrity": ["یکپارچگی", "duplicate", "تکراری"],
}


def _select_passes_for_inspector_focus(
    focus_notes: str,
    all_passes: List[str],
) -> List[str]:
    """Inspector chat-triggered scan: pick only passes relevant to user's request.

    Returns at most ~5 passes. Always includes a small core (frontend+backend)
    when nothing else matches so we don't end up with zero passes. If the user
    request mentions deploy/build, prioritizes dependency pass.
    """
    if not focus_notes or not focus_notes.strip():
        # No anchor — fall back to a sensible default (no 12-pass blowout)
        return [p for p in ["frontend", "backend", "functional_correctness"] if p in all_passes]
    text = focus_notes.lower()
    scored: List[Tuple[str, int]] = []
    for pass_id, kws in _INSPECTOR_PASS_KEYWORDS_FA.items():
        if pass_id not in all_passes:
            continue
        hits = sum(1 for kw in kws if kw.lower() in text)
        if hits > 0:
            scored.append((pass_id, hits))
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [p for p, _ in scored[:5]]
    # Safety net — always run functional_correctness if user described a bug/error
    if any(w in text for w in ("خطا", "error", "باگ", "bug", "broken", "نشد")):
        if "functional_correctness" in all_passes and "functional_correctness" not in selected:
            selected.append("functional_correctness")
    # If nothing matched at all, default to frontend+backend minimal
    if not selected:
        selected = [p for p in ["frontend", "backend"] if p in all_passes]
    return selected[:6]


async def _filter_proposals_by_relevance(
    service: Any,
    *,
    proposals: List[Dict[str, Any]],
    focus_notes: str,
    model_id: Optional[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Ask an LLM to keep only proposals relevant to user's request.

    Returns (kept, dropped). Falls back to (all, []) on any failure so we
    never silently lose work on an LLM hiccup.
    """
    if not proposals:
        return proposals, []
    # Build compact index for the LLM — id + title + first 200 chars description
    index_lines: List[str] = []
    for idx, p in enumerate(proposals):
        title = (p.get("title") or "").strip()[:150]
        desc = (p.get("description") or "").strip().replace("\n", " ")[:200]
        targets = ", ".join((p.get("target_files") or [])[:3])
        index_lines.append(f"{idx}|{title}|{desc}|{targets}")
    index_blob = "\n".join(index_lines)

    prompt = f"""تو یک فیلتر دقیق برای پیشنهادهای اسکن هستی.

کاربر این درخواست را در چت بازرس ویژه نوشته:
---
{focus_notes.strip()[:2000]}
---

اسکن این {len(proposals)} پیشنهاد را تولید کرده. هر سطر: `index|title|description|target_files`

{index_blob}

# وظیفه
فقط index پیشنهادهایی را برگردان که **مستقیماً به درخواست کاربر مربوط هستند**.
- اگر کاربر گفته «فرانت سفیده»، پیشنهادهای backend/cleanup/security_audit بی‌ربط‌اند → drop
- اگر کاربر گفته «دیپلوی نمی‌شه»، پیشنهادهای UI styling بی‌ربط‌اند → drop
- معیار: «اگر این پیشنهاد را اعمال کنم، آیا به حل مشکل/درخواست کاربر کمک می‌کند؟»
- در شک، نگه دار (better err on keeping than dropping)

# خروجی (فقط JSON)
{{"kept_indices": [0, 2, 5], "dropped_indices": [1, 3, 4]}}"""

    try:
        response = await service._ai_generate(
            prompt, model_id=model_id, max_tokens=600, temperature=0.0
        )
        parsed = service._extract_json(response) or {}
        kept_idx = set(int(i) for i in (parsed.get("kept_indices") or []) if isinstance(i, (int, str)))
    except Exception as e:
        logger.warning(f"relevance-filter: LLM call failed ({e}); keeping all")
        return proposals, []

    if not kept_idx:
        logger.warning("relevance-filter: LLM returned no kept indices; keeping all (safety)")
        return proposals, []

    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for idx, p in enumerate(proposals):
        if idx in kept_idx:
            kept.append(p)
        else:
            dropped.append(p)
    # Safety: if filter would drop everything, keep all
    if not kept:
        return proposals, []
    return kept, dropped


def _build_pass_prompt(
    pass_id: str,
    *,
    repo: str,
    user_goal: str,
    stacks: List[str],
    files_summary: str,
    deep_files_blob: str,
    package_files_blob: str,
    import_graph_summary: str = "",
    extra: str = "",
) -> str:
    base = f"""تو یک تحلیلگر senior software هستی. این یک فاز از یک اسکن چندفازی روی پروژهٔ زیر است.
خروجی تو پرامپت‌های اجرایی برای ابزار کدنویس (Cursor/Copilot) خواهد ساخت — پس باید **کاملاً مشخص و قابل اعمال** باشد.

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

# پروژه
{repo}
Stack تشخیص داده شده: {', '.join(stacks) or '(نامشخص)'}

# فایل‌ها (نمونه — مسیر کامل از ریشهٔ ریپو)
{files_summary}

# محتوای فایل‌های کلیدی (هر فایل با شمارهٔ خط)
{deep_files_blob}

# فایل‌های Dependency
{package_files_blob}
"""
    if import_graph_summary:
        base += f"\n# نقشهٔ Importهای داخلی (هاب‌ها و وابستگی‌ها)\n{import_graph_summary}\n"

    pass_specs = {
        "frontend": """
فاز فعلی: **A — تحلیل Frontend**
برای هر صفحه/کامپوننت مهم بنویس:
- چه می‌کند
- به کدام endpoint وصل است
- placeholder/TODO دارد؟
- dead link یا component undefined؟
- کاملاً کار می‌کند یا ناقص است؟
""",
        "backend": """
فاز فعلی: **B — تحلیل Backend**
برای هر endpoint مهم بنویس:
- پارامترها و response model
- آیا UI آن را call می‌کند؟ (در صورت قابل تشخیص)
- auth، rate-limit، validation، error handling داشته یا نه
- ناقص یا dummy؟
""",
        "cross_stack": """
فاز فعلی: **C — Cross-stack consistency**
- API call های فرانت‌اند که endpoint matching در backend ندارند
- Endpointهای backend که UI آنها را مصرف نمی‌کند
- mismatch در نام/method/فیلدها/status codes
""",
        "security": """
فاز فعلی: **D — امنیت**
- وابستگی‌های قدیمی/آسیب‌پذیر
- secret hardcoded، endpoint بدون auth، CORS باز، نبود rate-limit
- input validation ضعیف، الگوهای SQL injection / XSS
- شمول secret در client bundle
""",
        "integrity": """
فاز فعلی: **E — یکپارچگی Cross-cutting**
- آیا فیچرهای README پیاده شده‌اند؟
- feature flags سازگارند؟
- migrations با مدل‌ها sync اند؟
- conflict بین auth قدیمی/جدید، storage قدیمی/جدید
- duplicated logic در چند جا
""",
        "quality": """
فاز فعلی: **F — کیفیت کد**
- dead code، duplicate logic، over-engineering
- فایل‌های >۵۰۰ خط، توابع >۸۰ خط
- تست‌های گم‌شده برای route/component اصلی
- مستندات قدیمی/ناقص
""",
        "dependency": """
فاز فعلی: **G — ناسازگاری‌های runtime/dependency**
- mismatch بین Pipfile/lock files
- نسخه‌های ناسازگار react/next/typescript/python
- env variableهای reference شده ولی در .env.example نیامده
- import های شکسته/dead
""",
        "completeness": """
فاز فعلی: **H — Completeness check**
- آیا تمام بخش‌های لازم برای رسیدن به «هدف اصلی پروژه» پیاده شده‌اند؟
- فیچرهای half-done که شروع شده ولی تمام نشده‌اند
- placeholderها، mock dataهای جامانده، endpointهایی که فقط dummy response برمی‌گردانند
""",
        "security_deep": """
فاز فعلی: **I — اسکن امنیتی عمیق (مهاجرت از Health analysis)**

این pass تخصصی‌تر از pass D (security) است — علاوه بر findings عادی،
یک خلاصهٔ ساختاریافته با شمارش دقیق هم برمی‌گرداند.

تمرکز:
- **Hardcoded secrets**: API keys, tokens, passwords, JWT secrets,
  database URLs با password، AWS/GCP credentials
  مثال‌های الگو: AKIA[0-9A-Z]{16}، sk_live_..., ghp_..., bearer tokens
- **Sensitive files**: .env, .env.local, credentials.json, .pem, .key,
  service-account*.json, secrets.yml, htpasswd
- **License**: آیا LICENSE موجود است؟ سازگار با dependencies؟
  مثلاً GPL در پروژه‌ای که می‌خواهد commercial باشد؟
- **Vulnerable dependencies**: نسخه‌های قدیمی شناخته‌شده با CVE
  (lodash <4.17.21, log4j <2.17, ...)
- **CORS/Auth**: endpoint بدون auth، CORS=`*` در production،
  cookie بدون Secure/HttpOnly
- **Input validation**: SQL injection patterns، XSS، command injection

# خروجی JSON اضافی (علاوه بر findings عادی)
علاوه بر `findings[]`، یک کلید جدید `security_summary` هم برگردان:

{
  "findings": [...],
  "security_summary": {
    "secrets_count": 0,
    "secrets_files": ["path/to/file.py:line"],
    "license_status": "ok | missing | conflicting | unknown",
    "license_name": "MIT | Apache-2.0 | ...",
    "vulnerable_deps_count": 0,
    "vulnerable_deps": [{"name": "lodash", "version": "4.0.0", "cve": "CVE-...", "severity": "high"}],
    "sensitive_files_count": 0,
    "sensitive_files": [".env", "credentials.json"],
    "cors_open": false,
    "endpoints_without_auth_count": 0,
    "overall_security_score": 85
  }
}

`overall_security_score` 0-100 بر اساس فرمول وزن‌دار:
- 100 شروع، -20 برای هر secret، -10 برای هر vuln dep critical،
  -5 برای هر sensitive file بدون gitignore، -15 اگر license missing،
  -10 برای CORS باز.
حداقل 0.
""",
        "coverage": """
فاز فعلی: **J — تحلیل پوشش تست (مهاجرت از Health analysis)**

این pass شناسایی می‌کند فایل‌های source که فایل test متناظر ندارند یا
دارای پوشش ضعیف‌اند، و untested critical paths را پیشنهاد می‌دهد.

تشخیص فایل‌های test (الگوها):
- Python: `tests/`, `test_*.py`, `*_test.py`, `conftest.py`
- JS/TS: `__tests__/`, `*.test.{ts,tsx,js,jsx}`, `*.spec.*`,
  `cypress/`, `e2e/`, `tests/`
- جاوا: `src/test/`, `*Test.java`, `*Tests.java`
- سایر: `spec/`, `test/`

تمرکز:
- فایل‌های source که فایل test متناظر ندارند
- Critical paths (auth, payment, security) untested
- محاسبهٔ تخمینی coverage = (فایل‌های با test متناظر) / (کل source)
- پیشنهاد test cases مشخص برای ۳-۵ فایل critical untested

# خروجی JSON اضافی (علاوه بر findings عادی)
علاوه بر `findings[]` (هر کدام برای یک untested critical file)،
یک کلید جدید `coverage_summary` هم برگردان:

{
  "findings": [...],
  "coverage_summary": {
    "total_source_files": 0,
    "total_test_files": 0,
    "test_to_source_ratio": 0.0,
    "coverage_estimate_percent": 0,
    "untested_files_count": 0,
    "untested_files": ["path/to/file.py"],
    "critical_untested": [{"path": "...", "reason": "auth flow", "suggested_tests": ["test_login_invalid", "..."]}],
    "coverage_score": 75
  }
}

`coverage_score` 0-100:
- 100 اگر >80% فایل‌های source تست دارند
- proportional decrease تا 0 اگر هیچ تستی نیست

نکته: critical_untested فقط برای فایل‌هایی که در نقشهٔ Importهای داخلی
hub هستند یا critical_path (/auth/, /payment/, /security/) را شامل می‌شوند.
""",
        # 🆕 (P3) Pass K
        "logical_alignment": """
فاز فعلی: **K — همراستایی منطقی فایل‌ها/قابلیت‌ها**

برای هر فایل اصلی پروژه، **سه سؤال** را به‌صورت explicit جواب بده:
- (الف) **چه کاری می‌کند؟** نقش این فایل/قابلیت در کل پروژه چیست؟
- (ب) **در frontend کجا نمایان می‌شود؟** اگر backend است، کدام UI آن را
  مصرف می‌کند؟ اگر frontend است، چه داده‌ای را نمایش می‌دهد؟
- (ج) **آیا با file دیگری تضاد دارد؟** آیا قابلیتی که این فایل ارائه
  می‌دهد، در فایل دیگری duplicate شده؟ آیا با naming/contract فایل
  دیگری ناسازگار است؟

برای هر مورد ناسازگاری/تضاد/orphan، یک finding بساز:
- Orphan: backend endpoint بدون frontend caller (یا برعکس) → severity high
- Duplicate: همان قابلیت در دو فایل مختلف پیاده شده → severity medium
- Naming conflict: دو endpoint با path یکسان → severity high
- Contract mismatch: response shape backend با Type frontend match نمی‌کند → severity high
- Stale code: کد ای که هیچ‌جا استفاده نمی‌شود → severity low

مثال finding:
- title: "duplicate prompt builder در runtime_executor و oversight_strong_prompt"
- description: "هر دو فایل تابع build_prompt دارند با logic مختلف"
- target_files: ["runtime_executor.py", "oversight_strong_prompt.py"]
- type: "refactor"
- priority: "medium"
""",
        # 🆕 (P3) Pass L
        "functional_correctness": """
فاز فعلی: **L — صحت رفتاری per-feature**

برای هر قابلیت اصلی، edge case‌ها و failure modeها را شمارش کن:
- **Edge cases**: ورودی خالی، null، negative، خیلی بزرگ، Unicode، RTL
- **Error handling**: try/except missing، exception swallowed بدون log،
  no user-facing error message
- **Race conditions**: async که lock ندارد، shared state بدون mutex،
  concurrent writes
- **Failure modes**: API call بدون timeout، fetch بدون error handling،
  DB transaction بدون rollback
- **Security boundaries**: input validation missing، SQL injection vector،
  XSS vector، path traversal

برای هر مورد یک finding با severity بر اساس impact:
- critical: شکست production در شرایط نسبتاً عادی (مثل null user input)
- high: race condition یا exception swallowed در critical path
- medium: edge case کمتر رایج
- low: cosmetic یا rare edge case

**مهم**: فقط با شواهد قابل استناد در کد finding بساز. حدس نزن. اگر
احتمالی است، severity پایین بگذار با تذکر "نیاز به تأیید".

مثال finding:
- title: "exception swallowed در apply_followup_after_verify"
- description: "خط 2410، try/except عام بدون log کافی — fail silent"
- target_files: ["oversight_service.py:2410"]
- type: "bug"
- priority: "high"
""",
    }

    output = """
# خروجی فقط JSON خالص (بدون متن اضافی، بدون ```، بدون commentary)

برای **هر یافته**، باید این فیلدها را با حداکثر دقت پر کنی — وگرنه تسکی که از آن ساخته می‌شود برای ابزار کدنویس قابل اعمال نخواهد بود:

{
  "findings": [
    {
      "title": "عنوان کوتاه ۱ جمله‌ای و قابل سنجش",
      "type": "bug | refactor | docs | feature_request | security | other",
      "priority": "low | medium | high | critical",

      "description": "پاراگراف کامل: چرا این مشکل/نیاز است، چه تأثیری دارد، شواهد دیده‌شده در کد",

      "proposed_action": "پیشنهاد عملی دقیق برای رفع — چه کد/پیکربندی تغییر کند",

      "target_locations": [
        {
          "path": "backend/app/services/foo.py",
          "lines": "245-289",
          "symbol": "validate_token",
          "snippet": "def validate_token(t):\\n    return True  # ⚠️ هیچ بررسی expiry ندارد",
          "note": "تابع اصلی که باید اصلاح شود"
        }
      ],

      "related_files": [
        {"path": "backend/app/api/routes/auth.py", "reason": "این endpoint از validate_token استفاده می‌کند", "at_line": 67},
        {"path": "frontend/src/lib/api.ts", "reason": "client که login را call می‌کند"}
      ],

      "dependency_summary": "این تابع توسط ۳ روتر و یک hook فرانت‌اند استفاده می‌شود؛ تغییر آن روی کل auth flow اثر می‌گذارد.",

      "tech_context": "FastAPI + JWT + Next.js 14 App Router",

      "before_after_examples": [
        {"label": "نمونه expiry check",
         "before": "if token: return user",
         "after":  "if token and not is_expired(token): return user\\nelse: raise HTTPException(401)"}
      ],

      "acceptance_criteria": [
        "endpoint /api/login برای توکن منقضی ۴۰۱ برمی‌گرداند",
        "تابع validate_token پارامتر exp را چک می‌کند",
        "تست واحد جدید برای expiry اضافه شود"
      ],

      "validation_commands": [
        "pytest backend/tests/test_auth.py -k expiry",
        "npm run test -- login"
      ],

      "estimated_complexity": "small | medium | large",
      "risks": "احتمال شکستن sessionهای فعال؛ نیاز به migration کوتاه"
    }
  ]
}

# قوانین مهم:
1. **path** را همیشه از ریشهٔ ریپو بنویس (مثل `backend/app/...` یا `frontend/src/...`).
2. **lines** باید واقعی باشد — از شمارهٔ خط‌های نمایش‌داده‌شده در «محتوای فایل‌های کلیدی» استفاده کن.
3. **snippet** باید دقیقاً همان کدی باشد که در فایل اصلی آمده (می‌توانی truncate کنی با `...` ولی مسئلهٔ مورد نظر حتماً پیدا باشد).
4. **related_files** را از روی importهای واقعی پیدا کن — اگر در «نقشهٔ Importهای داخلی» نشان داده شده، آن را استفاده کن.
5. **acceptance_criteria** باید قابل تست باشد (نه تعریف کلی).
6. **حداکثر ۶ یافتهٔ مهم** برای این فاز. کیفیت > کمیت.
"""
    return base + (pass_specs.get(pass_id, "") + extra) + output


# =====================================================================
# Reusable deep-context builder — برای استفاده از سایر مسیرها (مثل
# idea_to_prompt) که نیاز به context عمیق پروژه دارند بدون اجرای کامل
# اسکن چندفازی.
# =====================================================================

def _with_line_numbers(content: str, max_lines: int = 400) -> str:
    """افزودن شمارهٔ خط به محتوای فایل."""
    lines = content.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... [TRUNCATED at line {max_lines} of {len(content.splitlines())}]"]
    width = len(str(len(lines)))
    return "\n".join(f"{str(i + 1).rjust(width)}: {ln}" for i, ln in enumerate(lines))


async def build_deep_context_for_idea(
    repo_full_name: str,
    *,
    branch: Optional[str] = None,
    token: Optional[str] = None,
    max_deep_read: int = 18,
    max_files_summary: int = 200,
    max_file_lines: int = 350,
    max_file_bytes: int = 50000,
    idea: str = "",  # 🆕 متن idea کاربر — برای keyword-aware ranking
) -> Dict[str, Any]:
    """ساخت context عمیق پروژه — برای استفاده در idea_to_prompt و سایر
    مسیرهایی که نیاز به محتوای واقعی فایل‌ها (با شمارهٔ خط) و گراف import
    دارند، نه صرفاً لیست نام فایل‌ها.

    این تابع همان منطق Phase 1 + Phase 2 از run_deep_scan را اجرا می‌کند
    ولی بدون شروع scan کامل (no progress file، no AI passes، فقط fetch
    و scoring و import graph).

    خروجی:
        {
          "ok": bool,
          "error": str,           # در صورت خطا
          "stacks": List[str],
          "files_count": int,
          "files_summary": str,    # "kind   path" برای 200 فایل اول
          "deep_files_blob": str,  # محتوای 18 فایل برتر با شمارهٔ خط
          "package_files_blob": str,
          "special_files_blob": str,  # README، CHANGELOG، docs
          "import_graph_summary": str,
          "deep_paths": List[str],  # مسیرهایی که deep-read شده‌اند
          "default_branch": str,
        }
    """
    if not token:
        return {"ok": False, "error": "توکن GitHub تنظیم نشده"}
    if not repo_full_name or "/" not in repo_full_name:
        return {"ok": False, "error": "repo_full_name نامعتبر"}

    headers = _gh_headers(token)

    async with aiohttp.ClientSession() as session:
        # Phase 1: tree + repo info
        info = await _gh_get_json(session, f"{GITHUB_API}/repos/{repo_full_name}", headers)
        default_branch = (info or {}).get("default_branch") or branch or "main"
        active_branch = branch or default_branch

        tree_data = await _gh_get_json(
            session,
            f"{GITHUB_API}/repos/{repo_full_name}/git/trees/{active_branch}?recursive=1",
            headers,
        )
        if not tree_data or "tree" not in tree_data:
            return {"ok": False, "error": "عدم دسترسی به ساختار پروژه"}

        all_files: List[str] = []
        sizes: Dict[str, int] = {}
        for item in tree_data["tree"]:
            if item.get("type") != "blob":
                continue
            p = item.get("path", "")
            if not p:
                continue
            low = p.lower()
            if any(low.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".otf", ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3")):
                continue
            if any(seg in low for seg in ("/node_modules/", "/.next/", "/dist/", "/build/", "/.git/", "/__pycache__/", "/.venv/", "/venv/")):
                continue
            all_files.append(p)
            sizes[p] = item.get("size", 0)

        kinds: Dict[str, str] = {p: _classify_file(p) for p in all_files}

        # خواندن dependency files
        dep_contents: Dict[str, str] = {}
        for fname in all_files:
            base = fname.split("/")[-1]
            if base in DEPENDENCY_FILES:
                content = await _fetch_file_content(session, repo_full_name, fname, headers, active_branch, 10000)
                if content:
                    dep_contents[base] = content

        stacks = _detect_stack(all_files, dep_contents)

        # 🆕 استخراج کلمات کلیدی از idea کاربر برای keyword-aware ranking
        # این یعنی فایل‌هایی که در path شان کلمات idea را دارند اولویت می‌گیرند
        idea_keywords = _extract_idea_keywords(idea) if idea else []
        if idea_keywords:
            logger.info(f"deep_context_for_idea: keywords extracted: {idea_keywords[:5]}...")

        # Phase 2: ابتدا rank سبک، سپس rerank با import graph
        # هر دو call با idea_keywords تا فایل‌های مرتبط با idea اولویت بگیرند
        ranked0 = _score_files(all_files, sizes, [], {}, idea_keywords=idea_keywords)
        initial_paths = [p for p, s in ranked0[: max_deep_read * 2] if s > 0][: max_deep_read * 2]

        deep_contents: Dict[str, str] = {}
        for p in initial_paths:
            try:
                c = await _fetch_file_content(session, repo_full_name, p, headers, active_branch, max_file_bytes)
                if c:
                    deep_contents[p] = c
            except Exception:
                continue

        # Import graph روی فایل‌های خوانده‌شده
        imports, imported_by, real_import_counts = _build_import_graph(deep_contents, all_files)

        # rerank با import_counts واقعی، انتخاب نهایی max_deep_read
        ranked = _score_files(all_files, sizes, [], real_import_counts, idea_keywords=idea_keywords)
        final_paths = [p for p, s in ranked[: max_deep_read] if s > 0]
        for p in final_paths:
            if p not in deep_contents:
                try:
                    c = await _fetch_file_content(session, repo_full_name, p, headers, active_branch, max_file_bytes)
                    if c:
                        deep_contents[p] = c
                except Exception:
                    continue

        # Special context: README، CHANGELOG، tsconfig، next.config، Dockerfile، …
        # 🆕 (P2) اضافه شد: Dockerfile, docker-compose, .env.example, Makefile,
        # tests config, CI configs — برای پوشش بهتر context
        _special_basenames = {
            "readme.md", "readme", "changelog.md", "tsconfig.json", "tsconfig.base.json",
            "next.config.js", "next.config.mjs", "vite.config.ts", "vite.config.js",
            ".env.example", ".env.sample", "dockerfile", "docker-compose.yml",
            "docker-compose.yaml", "makefile", "jest.config.js", "vitest.config.ts",
            "pytest.ini", "tox.ini", "setup.cfg", ".eslintrc.json", ".prettierrc",
        }
        special_files = [
            f for f in all_files
            if f.split("/")[-1].lower() in _special_basenames
            or f.startswith(("docs/", "documentation/", ".github/workflows/"))
        ][:12]  # 🆕 از 6 به 12 افزایش یافت
        special_contents: Dict[str, str] = {}
        for sp in special_files:
            try:
                c = await _fetch_file_content(session, repo_full_name, sp, headers, active_branch, 15000)
                if c:
                    special_contents[sp] = c
            except Exception:
                continue

        # ساخت blobها
        files_summary = "\n".join(
            f"{kinds.get(p, 'other'):>10}  {p}" for p in all_files[:max_files_summary]
        )
        # 🛡 (audit fix CRITICAL #2) — سقف total bytes برای جلوگیری از context overflow.
        # 60 فایل × 120KB = 7.2MB → برای GPT-4o/Claude خیلی زیاد. سقف ~3MB
        # (~750K tokens، در محدودهٔ Gemini 1M و Claude 200K). فایل‌های اولویت
        # بالاتر (با امتیاز بیشتر) اول می‌آیند، اگر cap رد شد توقف.
        TOTAL_BYTES_CAP = 3_000_000  # ~3MB total deep context
        deep_blob_parts: List[str] = []
        running_total = 0
        added_count = 0
        truncated_count = 0
        for p, c in list(deep_contents.items())[:max_deep_read]:
            piece = f"=== {p} ===\n{_with_line_numbers(c, max_file_lines)}"
            if running_total + len(piece) > TOTAL_BYTES_CAP:
                truncated_count = len(deep_contents) - added_count
                break
            deep_blob_parts.append(piece)
            running_total += len(piece) + 2  # +2 for "\n\n" separator
            added_count += 1
        if truncated_count > 0:
            deep_blob_parts.append(
                f"\n\n... [TOTAL CONTEXT CAP {TOTAL_BYTES_CAP // 1024 // 1024}MB رسید — "
                f"{truncated_count} فایل دیگر در deep_files نیامد. files_summary بالا "
                f"همهٔ فایل‌ها را نشان می‌دهد.]"
            )
        deep_files_blob = "\n\n".join(deep_blob_parts)
        package_files_blob = "\n\n".join(
            f"=== {n} ===\n{c[:4000]}" for n, c in dep_contents.items()
        )
        special_files_blob = "\n\n".join(
            f"=== {p} ===\n{c[:4000]}" for p, c in special_contents.items()
        )

        top_hubs = sorted(real_import_counts.items(), key=lambda x: x[1], reverse=True)[:12]
        import_graph_summary = ""
        if top_hubs:
            hub_lines = []
            for path, cnt in top_hubs:
                callers = imported_by.get(path, [])[:5]
                hub_lines.append(
                    f"- `{path}` — {cnt} فایل آن را import می‌کنند: "
                    + ", ".join(f"`{c}`" for c in callers)
                )
            import_graph_summary = "\n".join(hub_lines)

        return {
            "ok": True,
            "error": "",
            "stacks": stacks,
            "files_count": len(all_files),
            "files_summary": files_summary,
            "deep_files_blob": deep_files_blob,
            "package_files_blob": package_files_blob,
            "special_files_blob": special_files_blob,
            "import_graph_summary": import_graph_summary,
            "deep_paths": list(deep_contents.keys()),
            "default_branch": default_branch,
        }


# =====================================================================
# Smart finding merger (مهاجرت از Health analysis _merge_similar_issues)
# =====================================================================

def _normalize_title(title: str) -> str:
    """نرمال‌سازی title برای similarity comparison."""
    import re as _re
    s = (title or "").strip().lower()
    # حذف کلمات stop رایج
    for stop in ["the", "a", "an", "is", "are", "to", "of", "for", "in",
                 "و", "در", "از", "به", "که", "یک", "این", "آن"]:
        s = _re.sub(rf"\b{stop}\b", " ", s)
    # حذف punctuation و normalize whitespace
    s = _re.sub(r"[^\w\s]", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


def _title_similarity(a: str, b: str) -> float:
    """محاسبهٔ similarity سادهٔ Jaccard روی tokens (سریع، بدون dependencies)."""
    na = _normalize_title(a)
    nb = _normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    sa = set(na.split())
    sb = set(nb.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union > 0 else 0.0


# 🆕 (Phase 5 — bug 28) — Content fingerprint برای findings بدون target_files
# استخراج کلمات کلیدی محتوایی (شناسه‌ها، نام تابع/کلاس، نام فایل) از title +
# description. AI variance در wording را خنثی می‌کند.
def _content_fingerprint(text: str, max_tokens: int = 8) -> frozenset:
    """فنجر معنایی: کلمات «دلپذیر» را برمی‌دارد و sort شده برمی‌گرداند.

    «دلپذیر» = طول ≥ ۴ + حداقل یک حرف انگلیسی یا underscore (یعنی شناسهٔ
    احتمالی کد، نه واژگان عادی فارسی). این روی پروژه‌های real-world که
    finding ها به نام تابع/کلاس/فایل ارجاع می‌دهند بسیار خوب کار می‌کند.
    """
    import re as _re
    if not text:
        return frozenset()
    # توکن‌های احتمالی شناسه: حروف، اعداد، underscore، slash، نقطه
    tokens = _re.findall(r"[A-Za-z_][A-Za-z0-9_./\-]{3,}", text)
    # یکتا، lowercase
    uniq = []
    seen = set()
    for t in tokens:
        tl = t.lower().strip("./-_")
        if not tl or tl in seen:
            continue
        # فیلتر کلمات عمومی که info خاصی ندارند
        if tl in {"this", "that", "with", "from", "have", "been", "will",
                  "true", "false", "none", "type", "data", "code", "file",
                  "name", "list", "dict", "json", "test", "tests", "main",
                  "https", "http", "function", "class", "method", "value"}:
            continue
        seen.add(tl)
        uniq.append(tl)
        if len(uniq) >= max_tokens:
            break
    return frozenset(uniq)


def _content_fingerprint_match(
    a_title: str, a_desc: str,
    b_title: str, b_desc: str,
    min_overlap: float = 0.6,
    min_tokens: int = 3,
) -> bool:
    """آیا دو finding/task فنجر محتوایی مشابه دارند؟"""
    fa = _content_fingerprint(f"{a_title} {a_desc[:300]}")
    fb = _content_fingerprint(f"{b_title} {b_desc[:300]}")
    if len(fa) < min_tokens or len(fb) < min_tokens:
        return False
    inter = fa & fb
    smaller = min(len(fa), len(fb))
    overlap = len(inter) / smaller if smaller else 0.0
    return overlap >= min_overlap


def _merge_similar_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ادغام هوشمند findings مشابه — مهاجرت از Health analysis.

    منطق:
    1. findings با title exactly یکسان → ادغام
    2. findings با similarity > 0.8 + همان type → ادغام
    3. findings با target_files مشترک + همان type + پایه‌های مشابه → ادغام
    parent finding اول (highest priority، یا اول در ترتیب) باقی می‌ماند.
    دیگران در parent.merged_findings ذخیره می‌شوند.

    خروجی: لیست unique findings با merged_findings field.
    """
    if not findings:
        return []

    SIMILARITY_THRESHOLD = 0.8
    PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    # ابتدا بر اساس priority sort کن (critical اول)
    sorted_findings = sorted(
        findings,
        key=lambda f: PRIORITY_ORDER.get((f.get("priority") or "medium").lower(), 2),
    )

    unique: List[Dict[str, Any]] = []

    for f in sorted_findings:
        title = (f.get("title") or "").strip()
        if not title:
            continue

        ftype = (f.get("type") or "").lower()
        # 🆕 (Phase 5 — bug 6) — findings از scan_v5 (با _pass شروع‌شده با
        # "phase5_") نباید با dedup قدیمی merge شوند. هر stale/anti-pattern/
        # notification audit یک finding مستقل است (مثلاً 50 dead_endpoint
        # 50 task جداگانه است، نه 1 task).
        f_pass = (f.get("_pass") or "").lower()
        is_phase5 = f_pass.startswith("phase5_")
        f_files: set = set()
        for loc in (f.get("target_locations") or []):
            if isinstance(loc, dict) and loc.get("path"):
                f_files.add(loc["path"])
        for p in (f.get("target_files") or []):
            if isinstance(p, str):
                f_files.add(p)

        merged_into: Optional[Dict[str, Any]] = None

        # دنبال parent مناسب در unique بگرد
        for u in unique:
            u_title = (u.get("title") or "").strip()
            u_type = (u.get("type") or "").lower()
            u_pass = (u.get("_pass") or "").lower()
            sim = _title_similarity(title, u_title)

            # شرط ۱: exact match (sim=1.0)
            if sim >= 1.0:
                merged_into = u
                break

            # 🆕 (Phase 5) — Phase 5 finding ها فقط با خودشان merge می‌شوند
            # و فقط اگر title و file یکسان باشد (تا 50 dead_endpoint جدا
            # بمانند، نه یکی شوند)
            if is_phase5 or u_pass.startswith("phase5_"):
                # اگر هر دو phase5 و title و file هر دو exact match → merge
                # در غیر این صورت → جداگانه نگه دار
                if is_phase5 and u_pass.startswith("phase5_") and sim >= 0.95:
                    if f_files == set(p for loc in (u.get("target_locations") or []) for p in [loc.get("path", "")] if loc.get("path")):
                        merged_into = u
                        break
                continue

            # شرط ۲: similarity بالا و type یکسان (فقط non-phase5)
            if sim >= SIMILARITY_THRESHOLD and ftype == u_type and ftype:
                merged_into = u
                break

            # شرط ۳: target_files زیاد مشترک + type یکسان (target_files
            # similarity > 0.6 یعنی ادغام منطقی است)
            if ftype == u_type and ftype and f_files:
                u_files: set = set()
                for loc in (u.get("target_locations") or []):
                    if isinstance(loc, dict) and loc.get("path"):
                        u_files.add(loc["path"])
                for p in (u.get("target_files") or []):
                    if isinstance(p, str):
                        u_files.add(p)
                if u_files:
                    file_overlap = len(f_files & u_files) / len(f_files | u_files)
                    if file_overlap > 0.6:
                        merged_into = u
                        break

        if merged_into is not None:
            # اضافه کن به merged_findings parent
            mf = merged_into.setdefault("merged_findings", [])
            mf.append({
                "title": title,
                "type": ftype,
                "priority": f.get("priority"),
                "_pass": f.get("_pass"),
                "description": (f.get("description") or "")[:500],
            })
        else:
            # finding مستقل — به unique اضافه کن
            unique.append(f)

    return unique


# =====================================================================
# 🆕 (P2) Cross-scan deduplication
# =====================================================================

def _find_existing_active_task(
    service: Any,
    watched_id: str,
    finding: Dict[str, Any],
    similarity_threshold: float = 0.8,
) -> Optional[Any]:
    """در tasks active موجود (همان watched، نه archived/done/cancelled)
    دنبال match با finding بگرد.

    🆕 (Phase 5 — bug 26) — حالا match سه‌مرحله‌ای:
      ۱) structural fingerprint: (type + target_files overlap >= 50%)
         این برای findings AI-generated (coherence/anti_pattern) که هر اسکن
         تیتر کمی متفاوت تولید می‌کنند، حیاتی است.
      ۲) title Jaccard >= 0.8 (مثل قبل)
      ۳) fallback: تطابق با raw_idea تسک
    """
    try:
        finding_title = (finding.get("title") or "").strip()
        if not finding_title:
            return None
        finding_desc = (finding.get("description") or "")[:500]
        finding_type = str(finding.get("type") or "").lower()
        # 🆕 normalize target_files برای structural fingerprint
        finding_targets = {
            str(p).strip().lower() for p in (finding.get("target_files") or [])
            if p and isinstance(p, str)
        }
        # finding._pass و _source هم بخشی از fingerprint اند
        finding_pass = str(finding.get("_pass") or "").lower()

        candidates = [
            t for t in service.tasks
            if t.watched_id == watched_id
            and t.status not in ("done", "cancelled")
            and not getattr(t, "archived", False)
            # تسک‌هایی که verify done شده‌اند هم match نشوند (الان active match)
            and t.verification_status not in ("done",)
        ]
        for task in candidates:
            # 🆕 (bug 26) — مرحلهٔ ۱: structural fingerprint
            # اگر type یکی، _pass یکی، و target_files با ≥۵۰٪ overlap → دوپلیکیت
            task_type = str(getattr(task, "type", "") or "").lower()
            task_targets = {
                str(p).strip().lower() for p in (getattr(task, "target_files", None) or [])
                if p and isinstance(p, str)
            }
            task_meta = getattr(task, "created_by_scan_metadata", None) or {}
            # metadata key قبلاً '_pass' (با underscore) ذخیره شده — حواست باشد
            task_pass = str(
                (task_meta.get("_pass") or task_meta.get("pass"))
                if isinstance(task_meta, dict) else ""
            or "").lower()
            if (
                finding_type and task_type and finding_type == task_type
                and finding_targets and task_targets
            ):
                _inter = finding_targets & task_targets
                _union = finding_targets | task_targets
                _overlap = len(_inter) / len(_union) if _union else 0.0
                # اگر pass هم match کند، آستانه پایین‌تر کافی است
                _pass_match = bool(finding_pass and task_pass and finding_pass == task_pass)
                _thresh = 0.4 if _pass_match else 0.5
                if _overlap >= _thresh:
                    return task

            # 🆕 (bug 28) — مرحلهٔ ۲: content fingerprint برای findings
            # بدون target_files (مثل coherence/anti_pattern). شناسه‌های کد
            # (نام تابع/کلاس/فایل) را از title+description استخراج می‌کند —
            # AI wording variance را بی‌اثر می‌سازد. type باید یکی باشد.
            if (
                finding_type and task_type and finding_type == task_type
                and (not finding_targets or not task_targets)
            ):
                if _content_fingerprint_match(
                    finding_title, finding_desc,
                    task.title or "", task.raw_idea or "",
                ):
                    return task

            # مرحلهٔ ۳: تطابق با title
            sim_title = _title_similarity(finding_title, task.title)
            if sim_title >= similarity_threshold:
                return task
            # مرحلهٔ ۳ (fallback): تطابق با raw_idea (اگر کاربر title را edit کرده)
            if task.raw_idea:
                sim_raw = _title_similarity(finding_title, task.raw_idea)
                if sim_raw >= similarity_threshold:
                    return task
            # مرحلهٔ ۴ (fallback): finding.description با task.raw_idea
            if finding_desc and task.raw_idea:
                sim_desc = _title_similarity(finding_desc[:200], task.raw_idea[:200])
                if sim_desc >= similarity_threshold:
                    return task
        return None
    except Exception as _e:
        logger.debug(f"_find_existing_active_task failed: {_e}")
        return None


# =====================================================================
# Main deep scan function
# =====================================================================

async def run_deep_scan(
    watched_id: str,
    *,
    model_id: Optional[str] = None,
    model_ids: Optional[List[str]] = None,
    enabled_passes: Optional[List[str]] = None,
    deep_read_count: int = 35,
    selected_sections: Optional[List[str]] = None,
    custom_paths: Optional[List[str]] = None,
    include_dependencies: bool = True,
    focus_notes: Optional[str] = None,
    # 🆕 (inspector-scan) — وقتی این پارامتر `inspector_session:{id}` باشد،
    # خروجی scan هرگز به OversightTask DB نوشته نمی‌شود.
    output_target: Optional[str] = None,
    # 🆕 (v2 M2) — semantic search روی tree برای vague-intent. اگر این
    # غیرخالی است و selected_sections/custom_paths هر دو خالی‌اند، scope
    # به top 30 فایل match-ترین به این keywordها محدود می‌شود.
    semantic_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """اجرای کامل deep scan روی یک watched.

    🆕 (P1) پارامتر model_ids: اگر None یا یک‌مدلی، رفتار قبلی (single model).
    اگر چندتایی، هر pass با تمام مدل‌ها اجرا می‌شود و findings از همه
    مدل‌ها با _merge_similar_findings ادغام می‌شوند (consensus by similarity).

    🆕 (selective-scan) selected_sections + custom_paths: اگر هیچ‌کدام داده
    نشوند، اسکن کلی پروژه (رفتار قدیمی). در غیر این صورت، فقط فایل‌های
    متعلق به section های انتخابی + custom_paths اسکن می‌شوند. اگر
    include_dependencies=True، بعد از ساختن import graph، فایل‌های
    upstream/downstream یک‌سطح هم به selection اضافه می‌شوند تا
    «task های بررسی» همان‌طور که کاربر در voice خواست شامل وابستگی‌ها
    باشند.
    """
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise ValueError("پروژه یافت نشد")

    # 🆕 (inspector-scan) — parse output_target در ابتدای function تا بتوانیم
    # در همان فاز ۱ (scan_v5 session creation) هم gate کنیم.
    # `_output_target_session_id` همان `_inspector_session_id` است که بعداً
    # هم استفاده می‌شود — نام جدا فقط برای وضوح در gate های اولیه.
    _output_target_session_id: Optional[int] = None
    if output_target and output_target.startswith("inspector_session:"):
        try:
            _output_target_session_id = int(output_target.split(":", 1)[1])
        except (ValueError, IndexError):
            _output_target_session_id = None

    # 🆕 Mapping scan_depth → enabled_passes (مهاجرت از Health depth)
    # اگر enabled_passes صریحاً پاس داده شده، آن را استفاده کن
    # وگرنه از watched.scan_depth بخوان
    # 🆕 (P3) به‌روز: حالا ۱۲ pass موجود است (logical_alignment + functional_correctness اضافه شدند)
    if enabled_passes is None:
        # 🆕 (inspector-scoped-scan) — اگر این scan از Inspector chat آمده و
        # کاربر focus_notes داده، فقط passهای مرتبط با همان درخواست را اجرا
        # کن. این جلوی ۹۶ پیشنهاد بی‌ربط را می‌گیرد بدون اینکه قابلیت
        # auto-scan را حذف کند.
        if _output_target_session_id is not None and (focus_notes or "").strip():
            _all_pass_ids = [p[0] for p in PASSES]
            enabled_passes = _select_passes_for_inspector_focus(
                focus_notes or "", _all_pass_ids
            )
            logger.info(
                f"inspector-scoped-scan: focus_notes='{(focus_notes or '')[:120]}' → "
                f"selected passes={enabled_passes} (of {len(_all_pass_ids)})"
            )
        else:
            depth = getattr(watched, "scan_depth", "deep") or "deep"
            if depth == "quick":
                # سریع: فقط ۳ pass essential
                enabled_passes = ["frontend", "backend", "security_deep"]
            elif depth == "standard":
                # متعادل: ۶ pass (پنج تای قبلی + logical_alignment)
                enabled_passes = ["frontend", "backend", "security_deep",
                                  "quality", "completeness", "logical_alignment"]
            elif depth == "thorough":
                # کامل + per-file scoring + roadmap (همهٔ ۱۲)
                enabled_passes = [p[0] for p in PASSES]
            else:  # "deep" (default)
                # عمیق: همهٔ ۱۲ pass
                enabled_passes = [p[0] for p in PASSES]

    # 🆕 (Phase 5 — bug 19) — deep_read_count حالا depth-aware است.
    # default ۳۵ (× ۲ داخلی = ۷۰) برای پروژه‌های متوسط کفایت می‌کرد، ولی
    # برای ultra/thorough/deep باید پوشش بیشتری داشته باشیم.
    # 🆕 (bug A6) — ultra حالا UNCAPPED است؛ همهٔ فایل‌های پروژه deep-read
    # می‌شوند (تا سقف امن ۲۰۰۰ که از حد منطقی ریپوها بزرگ‌تر است).
    # کاربر می‌تواند با explicit deep_read_count override کند.
    if deep_read_count == 35:  # یعنی default، نه override
        _depth_now = getattr(watched, "scan_depth", "deep") or "deep"
        # ۲× داخلی هم اعمال می‌شود → effective:
        # balanced=70, deep=100, thorough=150, ultra=ALL (تا 2000)
        depth_map = {
            "quick": 25,
            "standard": 35,
            "balanced": 35,
            "deep": 50,
            "thorough": 75,
            "ultra": 2000,  # عملاً unlimited برای ریپوهای معمولی
        }
        deep_read_count = depth_map.get(_depth_now, 50)

    enabled = set(enabled_passes)

    write_progress(
        watched_id,
        status="starting",
        phase="init",
        message="آغاز deep scan",
        files_total=0,
        files_analyzed=0,
        passes_total=len(PASSES),
        passes_done=0,
        critical_count=0,
        findings_count=0,
        started_at=now_iso(),
    )

    # 🔔 notification (scan_started)
    try:
        from .notification_service import notification_service
        await notification_service.notify_event(
            "scan_started",
            f"🚀 *Deep Scan شروع شد*\n📁 `{watched.repo_full_name}`\n📊 *{len(enabled)}* pass فعال",
            subject="Scan started",
            priority="low",
            project_name=watched.repo_full_name,
            watched_id=watched_id,
        )
    except Exception as _e:
        logger.debug(f"scan_started notification skipped: {_e}")

    token = get_github_token()
    if not token:
        write_progress(watched_id, status="error", message="توکن GitHub تنظیم نشده")
        raise RuntimeError("توکن GitHub تنظیم نشده")

    headers = _gh_headers(token)
    repo = watched.repo_full_name

    async with aiohttp.ClientSession() as session:
        # ----- فاز ۱ -----
        write_progress(watched_id, phase="phase1_structure", message="بارگذاری ساختار پروژه")
        info = await _gh_get_json(session, f"{GITHUB_API}/repos/{repo}", headers)
        branch = (info or {}).get("default_branch") or watched.default_branch or "main"

        tree_data = await _gh_get_json(
            session,
            f"{GITHUB_API}/repos/{repo}/git/trees/{branch}?recursive=1",
            headers,
        )
        if not tree_data or "tree" not in tree_data:
            write_progress(watched_id, status="error", message="عدم دسترسی به tree پروژه")
            raise RuntimeError("عدم دسترسی به ساختار پروژه")

        all_files: List[str] = []
        sizes: Dict[str, int] = {}
        for item in tree_data["tree"]:
            if item.get("type") != "blob":
                continue
            p = item.get("path", "")
            if not p:
                continue
            # حذف فایل‌های باینری/حجیم رایج
            low = p.lower()
            if any(low.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".otf", ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3")):
                continue
            if any(seg in low for seg in ("/node_modules/", "/.next/", "/dist/", "/build/", "/.git/", "/__pycache__/", "/.venv/", "/venv/")):
                continue
            all_files.append(p)
            sizes[p] = item.get("size", 0)

        # 🆕 (selective-scan, audit fix #2) — pre-filter snapshot کل tree.
        # وقتی scope محدود اعمال می‌شود، resolver وابستگی‌ها (در فاز ۲)
        # باید کل repo را ببیند تا فایل‌های off-scope وابسته را پیدا کند.
        # اگر این snapshot را نگه نداریم، expand_with_dependencies روی
        # همان scope محدود کار می‌کند و عملاً هیچ dep جدیدی پیدا نمی‌شود.
        unfiltered_all_files: List[str] = list(all_files)
        unfiltered_sizes: Dict[str, int] = dict(sizes)

        # 🆕 (selective-scan) — اگر selection داده شده، all_files را قبل از
        # هر کار دیگری فیلتر کن تا تمام pipeline (scoring/reading/scanning)
        # روی همان زیرمجموعه عمل کند.
        scan_scope_meta: Optional[Dict[str, Any]] = None
        if selected_sections or custom_paths:
            try:
                from .scan_sections import (
                    detect_sections as _ss_detect,
                    filter_files_by_selection as _ss_filter,
                )
                _detected_sections = _ss_detect(all_files)
                _filtered = _ss_filter(
                    all_files,
                    selected_sections,
                    custom_paths,
                    detected_sections=_detected_sections,
                )
                if _filtered:
                    scan_scope_meta = {
                        "selected_sections": list(selected_sections or []),
                        "custom_paths": list(custom_paths or []),
                        "include_dependencies": include_dependencies,
                        "before_filter": len(all_files),
                        "after_filter": len(_filtered),
                        "focus_notes": (focus_notes or "").strip() or None,
                    }
                    all_files = _filtered
                    # sizes را هم به همان زیرمجموعه محدود کن
                    sizes = {p: sizes.get(p, 0) for p in all_files}
                    write_progress(
                        watched_id,
                        phase="phase1_scope_filter",
                        message=(
                            f"🎯 اسکن انتخابی: {scan_scope_meta['after_filter']} از "
                            f"{scan_scope_meta['before_filter']} فایل انتخاب شد"
                        ),
                    )
                else:
                    # 🔴 (scope-empty) — تا commit fa86f99 اینجا فقط
                    # fallback به scan کلی داشتیم. در transcript کاربر «منو
                    # برگردون به branch» اسکن `selected_sections=['backend']`
                    # چون scope=0 شد به scan کل پروژه fallback کرد و ۷۳
                    # پیشنهاد بی‌ربط ساخت.
                    #
                    # 🆕 (regression-fix audit) — abort فقط برای Inspector
                    # path. در Oversight Deep Scan endpoint (/api/scan/X/deep)
                    # رفتار قبلی (fallback به full scan) رو حفظ می‌کنیم تا
                    # UI موجود که این endpoint رو استفاده می‌کنه نشکنه.
                    if _output_target_session_id is None:
                        # Oversight path — legacy behavior: fallback to full scan
                        write_progress(
                            watched_id,
                            phase="phase1_scope_empty",
                            message="⚠️ هیچ فایلی با selection match نشد — برمی‌گردیم به اسکن کلی (Oversight legacy)",
                        )
                        # scan_scope_meta=None باقی می‌مونه → scan کلی
                    else:
                        # Inspector path — abort (prevent unrelated proposals)
                        write_progress(
                            watched_id,
                            status="completed",
                            phase="phase1_scope_empty_abort",
                            message=(
                                "🚫 scope با هیچ فایلی match نشد — اسکن انجام نمی‌شود "
                                "(جلوگیری از پیشنهادهای بی‌ربط)."
                            ),
                        )
                        # informational log در chat session
                        try:
                            from .scan_v5.scan_inspector_session import log_scan_message
                            log_scan_message(
                                session_id=_output_target_session_id,
                                role="assistant",
                                content=(
                                    "ℹ️ scan متوقف شد: scope انتخاب‌شده "
                                    f"(`{', '.join(selected_sections or ['—'])}`"
                                    f"{' + ' + str(len(custom_paths or [])) + ' مسیر سفارشی' if custom_paths else ''}) "
                                    "با هیچ فایلی در repo match نکرد. "
                                    "این یعنی درخواست شما احتمالاً نیاز به scan ندارد — "
                                    "به‌جای آن از chat ساده استفاده کن، یا scope را تنظیم کن."
                                ),
                                action_type="scan_aborted",
                                extra_data={
                                    "kind": "scan_aborted",
                                    "reason": "scope_empty",
                                    "selected_sections": list(selected_sections or []),
                                    "custom_paths": list(custom_paths or []),
                                },
                            )
                        except Exception as _log_e:
                            logger.debug(f"scan_aborted log failed: {_log_e}")
                        return {
                            "success": False,
                            "aborted": True,
                            "reason": "scope_empty",
                            "passes_run": 0,
                            "findings": 0,
                            "tasks_created": 0,
                            "message": "scope با هیچ فایلی match نشد",
                        }
            except Exception as _scope_e:
                write_progress(
                    watched_id,
                    phase="phase1_scope_error",
                    message=f"⚠️ خطا در فیلتر scope (ادامه با اسکن کلی): {str(_scope_e)[:120]}",
                )

        # دسته‌بندی
        kinds: Dict[str, str] = {p: _classify_file(p) for p in all_files}

        # کامیت‌های اخیر برای recent_changed_files
        commits = await _gh_get_json(
            session, f"{GITHUB_API}/repos/{repo}/commits?per_page=30", headers
        ) or []
        recent_changed: List[str] = []
        # برای کاهش API call ها، فقط لیست sha می‌گیریم؛ تغییر فایل‌ها از body اولیه commit نمی‌آید
        # ساده: فایل‌های بزرگ‌تر را به‌جای commit history وزن می‌دهیم
        # محتوای dependencyها
        dep_contents: Dict[str, str] = {}
        for fname in all_files:
            base = fname.split("/")[-1]
            if base in DEPENDENCY_FILES:
                content = await _fetch_file_content(session, repo, fname, headers, branch, 10000)
                if content:
                    dep_contents[base] = content

        stacks = _detect_stack(all_files, dep_contents)

        # ذخیرهٔ structure
        # (audit fix #7) — اگر در حال selective scan هستیم، structure را
        # روی full repo بنویس نه scope محدود؛ وگرنه دفعهٔ بعد که endpoint
        # `/scan/{id}/sections` از این cache می‌خواند، فقط بخشی از repo
        # را می‌بیند و picker UI ناقص نشان داده می‌شود.
        if scan_scope_meta:
            _struct_files = unfiltered_all_files[:2000]
            _struct_kinds = {p: _classify_file(p) for p in _struct_files}
            _struct_count = len(unfiltered_all_files)
        else:
            _struct_files = all_files[:2000]
            _struct_kinds = kinds
            _struct_count = len(all_files)
        structure = {
            "watched_id": watched_id,
            "repo": repo,
            "branch": branch,
            "scanned_at": now_iso(),
            "files_count": _struct_count,
            "stacks": stacks,
            "kinds": _struct_kinds,
            "files": _struct_files,
            "last_scope": scan_scope_meta,  # برای debug/visibility
        }
        try:
            _write_json(STRUCTURE_DIR / f"{watched_id}.json", structure)
        except Exception:
            pass

        write_progress(
            watched_id,
            phase="phase2_scoring",
            message="انتخاب فایل‌های کلیدی",
            files_total=len(all_files),
            stacks=stacks,
        )

        # ----- فاز ۲ -----
        # 🆕 (v2 M2) — semantic search روی tree برای vague-intent
        # اگر `semantic_keywords` داریم و scope صریح نداریم (selected_sections
        # و custom_paths خالی‌اند)، scope را به top 30 فایل match محدود می‌کنیم.
        # این منطبق با درخواست کاربر است: «جاهایی که به درخواست من شبیه‌تر هست».
        if semantic_keywords and not selected_sections and not custom_paths:
            try:
                # سرچ سطح ۱: نام و مسیر فایل (وزن ۲)
                name_score: Dict[str, int] = {}
                kws_low = [k.lower() for k in semantic_keywords if k]
                for f in all_files:
                    f_low = f.lower()
                    s = sum(2 for kw in kws_low if kw in f_low)
                    if s > 0:
                        name_score[f] = s
                # سرچ سطح ۲: محتوای dep files (وزن ۱)
                content_score: Dict[str, int] = {}
                for fname, ctnt in (dep_contents or {}).items():
                    c_low = (ctnt or "").lower()
                    s = sum(c_low.count(kw) for kw in kws_low)
                    if s > 0:
                        for path in all_files:
                            if path.split("/")[-1] == fname:
                                content_score[path] = content_score.get(path, 0) + s
                # ترکیب
                combined: Dict[str, int] = {}
                for path, s in name_score.items():
                    combined[path] = combined.get(path, 0) + s
                for path, s in content_score.items():
                    combined[path] = combined.get(path, 0) + s
                # یک sweep ranked-baseline برای fallback
                _baseline_ranked = _score_files(all_files, sizes, recent_changed, {})
                if combined:
                    ranked_sem = sorted(combined.items(), key=lambda x: -x[1])[:30]
                    semantic_scope = [p for p, _ in ranked_sem]
                    all_files = semantic_scope
                    sizes = {p: sizes.get(p, 0) for p in all_files}
                    if scan_scope_meta is None:
                        scan_scope_meta = {}
                    scan_scope_meta.update({
                        "mode": "semantic_search",
                        "semantic_keywords": semantic_keywords,
                        "matches_found": len(combined),
                        "scope_capped_at": len(all_files),
                        "focus_notes_preview": (focus_notes or "")[:300],
                    })
                    write_progress(
                        watched_id,
                        phase="phase1_semantic_filter",
                        message=(
                            f"🔍 جستجوی معنایی: {len(all_files)} فایل شبیه‌ترین "
                            f"به پیام انتخاب شد (از {len(combined)} match کل)"
                        ),
                    )
                else:
                    # هیچ match نبود — fallback به top 30 hub
                    all_files = [p for p, _ in _baseline_ranked[:30]]
                    sizes = {p: sizes.get(p, 0) for p in all_files}
                    if scan_scope_meta is None:
                        scan_scope_meta = {}
                    scan_scope_meta.update({
                        "mode": "semantic_search_no_match",
                        "semantic_keywords": semantic_keywords,
                        "fallback": "top_30_hub_files",
                    })
                    write_progress(
                        watched_id,
                        phase="phase1_semantic_no_match",
                        message=(
                            f"⚠️ هیچ semantic match با keywords {semantic_keywords[:3]} "
                            f"پیدا نشد — به top 30 فایل hub fallback شد"
                        ),
                    )
            except Exception as _sem_e:
                write_progress(
                    watched_id,
                    phase="phase1_semantic_error",
                    message=f"⚠️ خطا در جستجوی معنایی: {str(_sem_e)[:120]}",
                )

        # ابتدا یک sweep سبک: top-N اولیه را با نوع/حجم/critical path رتبه‌بندی کن
        ranked0 = _score_files(all_files, sizes, recent_changed, {})
        # 🆕 (bug A6b) — در ultra، فیلتر s>0 برداشته می‌شود تا همهٔ فایل‌ها
        # (حتی موارد "other" مثل .md، .json، config) deep-read شوند.
        # دلیل: عدد "231/201" در UI به این علت می‌آمد که ۳۰ فایل score=0
        # داشتند (مارک‌داون، JSON config، ...). ultra واقعاً "همه چیز" است.
        _depth_now = (getattr(watched, "scan_depth", "deep") or "deep").lower()
        _filter_score = _depth_now != "ultra"
        if _filter_score:
            initial_deep_paths = [p for p, s in ranked0[: max(deep_read_count, 5) * 2] if s > 0]
        else:
            initial_deep_paths = [p for p, _s in ranked0[: max(deep_read_count, 5) * 2]]

        # خواندن این فایل‌ها (محتوای کامل ولی truncate شده)
        deep_contents: Dict[str, str] = {}
        for i, p in enumerate(initial_deep_paths):
            write_progress(
                watched_id,
                phase="phase2_reading",
                message=f"خواندن فایل‌های کلیدی ({i + 1}/{len(initial_deep_paths)})",
                files_analyzed=i + 1,
            )
            try:
                c = await _fetch_file_content(session, repo, p, headers, branch, 60000)
                if c:
                    deep_contents[p] = c
            except Exception:
                continue

        # حالا گراف Importهای واقعی را روی محتوای deep بسازیم
        write_progress(watched_id, phase="phase2_imports", message="ساخت نقشهٔ Importها")
        imports, imported_by, real_import_counts = _build_import_graph(deep_contents, all_files)

        # 🆕 (selective-scan) — اگر در حال scan انتخابی هستیم و
        # include_dependencies=True، فایل‌های upstream/downstream یک‌سطح
        # را به all_files اضافه کن.
        #
        # (audit fix #2 + #6) — resolver باید `unfiltered_all_files` را
        # ببیند (نه scope filtered)، وگرنه هیچ dependency خارج از scope
        # شناسایی نمی‌شود. علاوه بر این، برای detect upstream یک نمونه از
        # فایل‌های off-scope (پایتون/جاوااسکریپت) هم خوانده می‌شود — وگرنه
        # فقط dependents از داخل scope پیدا می‌شدند که عملاً همیشه خالی است.
        if scan_scope_meta and include_dependencies:
            try:
                from .scan_sections import expand_with_dependencies as _ss_expand

                # یک sweep سبک upstream-detection: تا ۸۰ فایل code که
                # داخل scope نیستند ولی ممکن است selected ها را import کنند.
                _off_scope_candidates = [
                    p for p in unfiltered_all_files
                    if p not in set(all_files)
                    and p.lower().endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"))
                ][:80]
                _off_scope_contents: Dict[str, str] = {}
                for _osp in _off_scope_candidates:
                    if _osp in deep_contents:
                        continue
                    try:
                        _c = await _fetch_file_content(session, repo, _osp, headers, branch, 40000)
                        if _c:
                            _off_scope_contents[_osp] = _c
                    except Exception:
                        continue

                _merged_contents: Dict[str, str] = dict(deep_contents)
                _merged_contents.update(_off_scope_contents)

                _expand_result = _ss_expand(
                    selected_files=list(all_files),
                    all_files=unfiltered_all_files,  # ← کل repo، نه scope
                    file_contents=_merged_contents,
                )
                _expanded = list(_expand_result.get("expanded") or [])
                _new_deps = [p for p in _expanded if p not in set(all_files)]
                if _new_deps:
                    all_files = all_files + _new_deps
                    sizes.update({p: unfiltered_sizes.get(p, 0) for p in _new_deps})
                    # محتویاتی که در sweep اضافی خواندیم را به deep_contents
                    # هم اضافه کن تا passes آن‌ها را ببینند (ولی هزینهٔ
                    # خواندن دوباره را ندهند)
                    for _np in _new_deps:
                        if _np in _off_scope_contents and _np not in deep_contents:
                            deep_contents[_np] = _off_scope_contents[_np]
                    scan_scope_meta["dependencies_added"] = len(_new_deps)
                    scan_scope_meta["deps_downstream"] = _expand_result.get("deps_added") or []
                    scan_scope_meta["deps_upstream"] = _expand_result.get("dependents_added") or []
                    write_progress(
                        watched_id,
                        phase="phase2_deps_expanded",
                        message=(
                            f"🔗 {len(_new_deps)} فایل وابسته (upstream/downstream) اضافه شد "
                            f"— scope نهایی: {len(all_files)} فایل"
                        ),
                    )
            except Exception as _dep_e:
                write_progress(
                    watched_id,
                    phase="phase2_deps_error",
                    message=f"⚠️ خطا در expand وابستگی‌ها: {str(_dep_e)[:120]}",
                )

        # rerank با import_counts واقعی
        ranked = _score_files(all_files, sizes, recent_changed, real_import_counts)
        final_deep_paths = [p for p, s in ranked[: max(deep_read_count, 5)] if s > 0]
        # هر فایل جدیدی که در sweep اول نخوانده‌ایم را الان بخوان
        for p in final_deep_paths:
            if p not in deep_contents:
                try:
                    c = await _fetch_file_content(session, repo, p, headers, branch, 60000)
                    if c:
                        deep_contents[p] = c
                except Exception:
                    continue

        # خواندن فایل‌های context ویژه: README، docs، config
        special_files = [
            f for f in all_files
            if f.split("/")[-1].lower() in ("readme.md", "readme", "changelog.md")
            or f.startswith(("docs/", "documentation/"))
            or f in ("tsconfig.json", "next.config.js", "next.config.mjs", "vite.config.ts", ".env.example")
        ][:8]
        special_contents: Dict[str, str] = {}
        for sp in special_files:
            try:
                c = await _fetch_file_content(session, repo, sp, headers, branch, 20000)
                if c:
                    special_contents[sp] = c
            except Exception:
                continue

        # ساخت context — files_summary با kind برای راهنمایی AI
        files_summary = "\n".join(
            f"{kinds.get(p, 'other'):>10}  {p}" for p in all_files[:300]
        )

        def _with_line_numbers(content: str, max_lines: int = 400) -> str:
            """افزودن شمارهٔ خط برای هر سطر — تا AI بتواند line range دقیق برگرداند."""
            lines = content.splitlines()
            if len(lines) > max_lines:
                lines = lines[:max_lines] + [f"... [TRUNCATED at line {max_lines} of {len(content.splitlines())}]"]
            width = len(str(len(lines)))
            return "\n".join(f"{str(i + 1).rjust(width)}: {ln}" for i, ln in enumerate(lines))

        # هر فایل تا ۴۰۰ خط با line numbers — حداکثر ۲۵ فایل deep
        deep_files_blob = "\n\n".join(
            f"=== {p} ===\n{_with_line_numbers(c, 400)}"
            for p, c in list(deep_contents.items())[:25]
        )
        package_files_blob = "\n\n".join(
            f"=== {n} ===\n{c[:4000]}" for n, c in dep_contents.items()
        )
        if special_contents:
            package_files_blob += "\n\n" + "\n\n".join(
                f"=== {p} ===\n{c[:4000]}" for p, c in special_contents.items()
            )

        # خلاصهٔ گراف Imports برای پاس به AI (فقط top hubs)
        top_hubs = sorted(real_import_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        import_graph_summary = ""
        if top_hubs:
            hub_lines = []
            for path, cnt in top_hubs:
                callers = imported_by.get(path, [])[:5]
                hub_lines.append(f"- `{path}` — {cnt} فایل آن را import می‌کنند: {', '.join(f'`{c}`' for c in callers)}")
            import_graph_summary = "\n".join(hub_lines)

        # ----- فاز ۳ -----
        all_findings: List[Dict[str, Any]] = []
        passes_done = 0
        critical_count = 0
        # 🆕 خلاصه‌های ساختاریافته از هر pass (مثلاً security_summary از
        # security_deep، coverage_summary از coverage). در structure scan
        # ذخیره می‌شوند تا UI /oversight بدون reparse findings نمایش دهد.
        pass_summaries: Dict[str, Any] = {}

        for pass_id, pass_label in PASSES:
            if pass_id not in enabled:
                continue
            # 🆕 چک pause/stop در شروع هر pass (graceful interruption)
            current_progress = read_progress(watched_id) or {}
            if current_progress.get("stop_requested"):
                write_progress(
                    watched_id, status="stopped",
                    message=f"scan با درخواست کاربر متوقف شد (پس از {passes_done} pass)",
                )
                logger.info(f"deep_scan stopped by user at pass={pass_id}")
                # خروج زودهنگام — هیچ task ساخته نمی‌شود
                return {
                    "success": False,
                    "stopped": True,
                    "passes_run": passes_done,
                    "findings": len(all_findings),
                    "tasks_created": 0,
                }
            # pause: تا زمان clear، صبر می‌کنیم (با timeout عمومی ۱۰ دقیقه)
            if current_progress.get("pause_requested"):
                pause_start = asyncio.get_event_loop().time()
                while True:
                    await asyncio.sleep(2)
                    cp = read_progress(watched_id) or {}
                    if not cp.get("pause_requested") or cp.get("stop_requested"):
                        break
                    if asyncio.get_event_loop().time() - pause_start > 600:
                        # timeout — خودکار resume
                        logger.warning(f"deep_scan pause timeout at pass={pass_id}")
                        break
                # دوباره stop چک کن (ممکن است در حین pause رسیده باشد)
                if (read_progress(watched_id) or {}).get("stop_requested"):
                    write_progress(
                        watched_id, status="stopped",
                        message=f"scan متوقف شد (پس از pause)",
                    )
                    return {
                        "success": False, "stopped": True,
                        "passes_run": passes_done,
                        "findings": len(all_findings), "tasks_created": 0,
                    }
            write_progress(
                watched_id,
                phase=f"phase3_{pass_id}",
                message=f"در حال {pass_label}",
                passes_done=passes_done,
            )
            # 🆕 (selective-scan + focus-notes) — اگر scope محدود است یا
            # کاربر یادداشت نقطه‌ای داده، یک بلوک به پایان pass prompt اضافه
            # کن. این بخش به هر pass بدون استثنا تزریق می‌شود تا همه
            # phaseها متمرکز بمانند.
            _extra_block = ""
            if scan_scope_meta:
                _ss = scan_scope_meta.get("selected_sections") or []
                _cp = scan_scope_meta.get("custom_paths") or []
                _inc = scan_scope_meta.get("include_dependencies", True)
                _fn = scan_scope_meta.get("focus_notes") or ""
                _extra_block = (
                    "\n\n# 🎯 محدودهٔ اسکن (Selective Scan — اولویت قطعی)\n"
                    "این یک اسکن انتخابی است. روی همین scope تمرکز کن و "
                    "task هایی خارج از این محدوده پیشنهاد نده.\n"
                    + (f"- بخش‌های انتخاب‌شده: {', '.join(_ss)}\n" if _ss else "")
                    + (f"- مسیرهای سفارشی: {', '.join(_cp)}\n" if _cp else "")
                    + (
                        "- 🔗 وابستگی‌ها هم پوشش داده شوند: upstream "
                        "(فایل‌هایی که این‌ها را import می‌کنند) + downstream "
                        "(فایل‌هایی که این‌ها import می‌کنند). در فایل‌های فوق "
                        "هر دو دسته اضافه شده‌اند.\n"
                        if _inc
                        else "- فقط فایل‌های انتخاب‌شده (بدون expand به وابستگی‌ها).\n"
                    )
                )
                if _fn:
                    _extra_block += (
                        "\n## ⚠️ توضیحات نقطه‌ای کاربر (HIGHEST PRIORITY)\n"
                        "کاربر دربارهٔ همین scope این یادداشت را داده. "
                        "این مهم‌ترین راهنماست — task هایت را حول این محورها "
                        "بساز، حتی اگر مشکلات دیگری هم در همان scope دیدی، "
                        "اولویت با این موارد است:\n\n"
                        + _fn.strip()
                        + "\n\n"
                        # 🆕 (v3 chat-history) — راهنمای صریح برای استفادهٔ
                        # context پیشین فقط در صورت مرتبط بودن
                        + "📋 **اگر در یادداشت فوق بخش `[📜 context پیشین]` می‌بینی**: "
                        + "این پیام‌های قبلی session هستند. آن‌ها را فقط برای فهم بهتر "
                        + "درخواست **اخیر** کاربر استفاده کن (مثلاً وقتی کاربر می‌گوید "
                        + "«اون فایل قبلی رو هم درست کن»). اگر context پیشین به درخواست "
                        + "اخیر **بی‌ربط** است، آن را نادیده بگیر — task ساختن روی موضوع "
                        + "قدیمی فقط چون در history بود اشتباه است.\n"
                    )
            prompt = _build_pass_prompt(
                pass_id,
                repo=repo,
                user_goal=watched.user_notes or "",
                stacks=stacks,
                files_summary=files_summary,
                deep_files_blob=deep_files_blob,
                package_files_blob=package_files_blob,
                import_graph_summary=import_graph_summary,
                extra=_extra_block,
            )
            try:
                # 🆕 (P1) consensus mode: اگر model_ids چندتایی، هر pass با همه
                # اجرا می‌شود و findings از مدل‌ها merge می‌شوند
                models_to_run: List[Optional[str]] = (
                    list(model_ids) if (model_ids and len(model_ids) > 1)
                    else [model_id]
                )
                pass_findings: List[Dict[str, Any]] = []
                pass_summaries_local: Dict[str, Any] = {}
                for mid in models_to_run:
                    try:
                        response = await service._ai_generate(
                            prompt, model_id=mid, max_tokens=4500, temperature=0.2
                        )
                        parsed = service._extract_json(response) or {}
                        m_findings = parsed.get("findings") or []
                        for f in m_findings:
                            f["_pass"] = pass_id
                            f["_model"] = mid or "default"
                            pass_findings.append(f)
                        for sum_key in ("security_summary", "coverage_summary"):
                            if isinstance(parsed.get(sum_key), dict):
                                pass_summaries_local[sum_key] = parsed[sum_key]
                    except Exception as me:
                        logger.warning(
                            f"deep_scan pass {pass_id} model {mid} failed: {me}"
                        )
                # consensus: ادغام findings مشابه از مدل‌های مختلف
                if len(models_to_run) > 1:
                    pass_findings = _merge_similar_findings(pass_findings)
                for f in pass_findings:
                    if f.get("priority") == "critical":
                        critical_count += 1
                all_findings.extend(pass_findings)
                for k, v in pass_summaries_local.items():
                    pass_summaries[k] = v
                write_progress(
                    watched_id,
                    findings_count=len(all_findings),
                    critical_count=critical_count,
                )
            except Exception as e:
                logger.warning(f"deep_scan pass {pass_id} failed: {e}")

            passes_done += 1
            write_progress(watched_id, passes_done=passes_done)

        # ----- فاز ۴: تجمیع، dedup هوشمند، اولویت‌بندی -----
        # (مهاجرت از Health analysis _merge_similar_issues — قبلاً فقط
        # exact-match dedup روی title بود؛ حالا با similarity score و
        # ادغام target_files مشترک)
        write_progress(watched_id, phase="phase4_aggregate", message="dedup هوشمند و ادغام")

        # 🆕 (Phase 5 — bug 9 fix) — `phase5_findings_to_standard` و
        # محاسبه `unique` به انتهای پایپ‌لاین (پس از اجرای ماژول‌های Phase 5)
        # منتقل شدند. در غیر این صورت در زمان فراخوانی، متغیرهای
        # `scan_v5_stale`/`scan_v5_anti_patterns`/... هنوز تعریف نشده‌اند
        # و NameError سکوت‌شده باعث می‌شد هیچ Phase 5 finding وارد
        # `all_findings` نشود (دلیل اصلی ۱۴ تسک از ۳۴۰ یافته).

        # ----- فاز ۴.۵: محاسبهٔ per-file health map -----
        # (مهاجرت از Health analysis file_health_map)
        # برای هر فایل deep-read شده، یک score 0-100 محاسبه می‌شود بر اساس:
        #   - تعداد findings مرتبط (severity weighted)
        #   - وزن‌های کاربر (scan_criteria_weights)
        # خروجی در structure ذخیره می‌شود تا UI heatmap نمایش دهد.
        weights = getattr(watched, "scan_criteria_weights", None) or {
            "security": 1.5, "quality": 1.0, "tests": 1.2, "completeness": 1.0,
            # 🆕 (P3) defaults برای dimensions جدید
            "logical_alignment": 1.0, "functional_correctness": 1.5,
        }
        SEVERITY_PENALTY = {"critical": 25, "high": 12, "medium": 5, "low": 2}
        # mapping pass_id → criteria key برای weight lookup
        PASS_TO_CRITERIA = {
            "security": "security", "security_deep": "security",
            "quality": "quality", "coverage": "tests",
            "completeness": "completeness",
            "frontend": "quality", "backend": "quality",
            "cross_stack": "quality", "integrity": "quality",
            "dependency": "quality",
            # 🆕 (P3) two new pass mappings
            "logical_alignment": "logical_alignment",
            "functional_correctness": "functional_correctness",
        }

        # 🆕 (Phase 5 — فاز ۱) — Comprehensive Inventory + Purpose Extraction
        # این بلوک fail-soft است: اگر scan_v5 import شکست خورد یا AI خاموش
        # بود، scan قدیمی ادامه می‌دهد بدون اختلال.
        scan_v5_inventory: Dict[str, Any] = {}
        scan_v5_purpose_map: Dict[str, Any] = {}
        try:
            write_progress(
                watched_id, phase="phase5_inventory",
                message="ساخت inventory جامع (۱۲ لایه)",
            )
            from .scan_v5.comprehensive_inventory import build_inventory
            scan_v5_inventory = build_inventory(deep_contents, all_files)
            logger.info(
                f"scan_v5 inventory: {scan_v5_inventory.get('_meta', {}).get('counts', {})}"
            )
        except Exception as _e_inv:
            logger.warning(f"scan_v5 inventory failed: {_e_inv}")

        try:
            write_progress(
                watched_id, phase="phase5_purpose",
                message="استخراج هدف و منطق فایل‌های کلیدی",
            )
            from .scan_v5.purpose_extractor import extract_purposes
            # task history برای originating_task_id
            _task_history_for_purpose = [
                {
                    "id": t.id,
                    "target_files": list(t.target_files or []),
                    "raw_idea": (t.raw_idea or "")[:500],
                }
                for t in service.tasks
                if getattr(t, "watched_id", None) == watched_id
            ][:50]
            scan_v5_purpose_map = await extract_purposes(
                inventory=scan_v5_inventory,
                file_contents=deep_contents,
                reverse_imports=imported_by,
                task_history=_task_history_for_purpose,
                commit_history=[],  # commits در scan قدیمی fetched نمی‌شود
                verify_model_id=(model_ids[0] if model_ids else model_id),
            )
            logger.info(
                f"scan_v5 purpose_map: {len(scan_v5_purpose_map)} files purposed"
            )
        except Exception as _e_pp:
            logger.warning(f"scan_v5 purpose extraction failed: {_e_pp}")

        # 🆕 (Phase 5 — فاز ۲) — Stale Detection + Feature Inventory
        scan_v5_stale: Dict[str, Any] = {"structural": [], "semantic": [], "summary": {}}
        scan_v5_feature_docs: List[Dict[str, Any]] = []
        try:
            if getattr(watched, "stale_detection_enabled", True):
                write_progress(
                    watched_id, phase="phase5_stale",
                    message="تشخیص گزینه‌های قدیمی و dead code",
                )
                from .scan_v5.stale_detector import detect_stale
                scan_v5_stale = detect_stale(
                    inventory=scan_v5_inventory,
                    purpose_map=scan_v5_purpose_map,
                    file_contents=deep_contents,
                    imported_by=imported_by,
                    runtime_state=None,  # Phase 4 می‌آورد
                )
                logger.info(
                    f"scan_v5 stale: {scan_v5_stale.get('summary')}"
                )

                # AI documentation برای options
                write_progress(
                    watched_id, phase="phase5_documenting",
                    message="مستندسازی گزینه‌ها با AI",
                )
                from .scan_v5.feature_documenter import document_features
                scan_v5_feature_docs = await document_features(
                    inventory=scan_v5_inventory,
                    purpose_map=scan_v5_purpose_map,
                    stale_findings=scan_v5_stale,
                    verify_model_id=(model_ids[0] if model_ids else model_id),
                )
                logger.info(
                    f"scan_v5 feature_docs: {len(scan_v5_feature_docs)} items documented"
                )
        except Exception as _e_stale:
            logger.warning(f"scan_v5 stale/document failed: {_e_stale}")

        # 🆕 (Phase 5 — فاز ۴) — Scan Inspector Session + Runtime + Outcome
        scan_v5_session_id: Optional[int] = None
        scan_v5_runtime_state: Dict[str, Any] = {}
        scan_v5_outcome_data: Dict[str, Any] = {}
        scan_v5_effectiveness_issues: List[Dict[str, Any]] = []
        try:
            # (audit fix I2) — در حالت Inspector scan موردی، scan_v5 session
            # جدید نسازیم؛ این scan در همان session chat در حال اجراست و یک
            # session موازی در مرکز نظارت سردرگم‌کننده است.
            if getattr(watched, "inspector_session_enabled", True) and _output_target_session_id is None:
                from .scan_v5.scan_inspector_session import (
                    create_scan_session, log_scan_message,
                )
                scan_v5_session_id = create_scan_session(
                    watched_id=watched_id,
                    project_name=getattr(watched, "name", "") or getattr(watched, "repo_full_name", ""),
                )
                if scan_v5_session_id:
                    log_scan_message(
                        scan_v5_session_id, "system",
                        f"🔍 شروع scan v5 — inventory: "
                        f"{len(scan_v5_inventory.get('files', []))} files, "
                        f"stale: {scan_v5_stale.get('summary', {})}",
                    )

            # Runtime discovery (R14)
            if getattr(watched, "runtime_discovery_enabled", True):
                write_progress(
                    watched_id, phase="phase5_runtime",
                    message="کشف state واقعی frontend + backend logs",
                )
                from .scan_v5.runtime_discovery import discover_runtime_state
                _ss = None
                try:
                    _ss = getattr(watched, "runtime_storage_state", None)
                except Exception:
                    pass
                # screenshot dir
                from pathlib import Path as _P
                _sd = _P("storage/scan_v5_screenshots") / str(watched_id)
                _sd.mkdir(parents=True, exist_ok=True)
                scan_v5_runtime_state = await discover_runtime_state(
                    frontend_base_url=getattr(watched, "frontend_base_url", None),
                    backend_base_url=getattr(watched, "backend_base_url", None),
                    inventory=scan_v5_inventory,
                    storage_state=_ss,
                    scan_session_id=scan_v5_session_id,
                    screenshot_dir=str(_sd),
                    verify_model_id=(model_ids[0] if model_ids else model_id),
                )
                logger.info(
                    f"scan_v5 runtime: "
                    f"alive={len(scan_v5_runtime_state.get('routes_alive', []))}, "
                    f"404={len(scan_v5_runtime_state.get('routes_404', []))}"
                )

            # Outcome data + effectiveness (R11)
            if getattr(watched, "outcome_data_enabled", True):
                write_progress(
                    watched_id, phase="phase5_outcome",
                    message="جمع‌آوری outcome data و audit effectiveness",
                )
                from .scan_v5.outcome_analyzer import (
                    collect_outcome_data, audit_effectiveness,
                )
                # render logs از 30 روز
                _render_logs: List[Dict[str, Any]] = []
                try:
                    from .verify_runtime.backend_log_probe import _fetch_relevant_logs
                    _render_logs = await _fetch_relevant_logs(
                        target_files=[], endpoints=[], symbols=[],
                        window_hours=720,
                    )
                except Exception as _le:
                    logger.debug(f"render logs fetch failed: {_le}")
                scan_v5_outcome_data = collect_outcome_data(
                    inventory=scan_v5_inventory,
                    purpose_map=scan_v5_purpose_map,
                    render_logs=_render_logs,
                )
                if getattr(watched, "logic_audit_enabled", True):
                    scan_v5_effectiveness_issues = await audit_effectiveness(
                        outcome_data=scan_v5_outcome_data,
                        purpose_map=scan_v5_purpose_map,
                        verify_model_id=(model_ids[0] if model_ids else model_id),
                    )
                    if scan_v5_session_id:
                        from .scan_v5.scan_inspector_session import log_scan_message
                        log_scan_message(
                            scan_v5_session_id, "system",
                            f"📊 effectiveness: {scan_v5_outcome_data.get('project_type')} — "
                            f"{len(scan_v5_effectiveness_issues)} issue identified",
                        )
        except Exception as _e_r4:
            logger.warning(f"scan_v5 phase 4 failed: {_e_r4}")

        # 🆕 (Phase 5 — فاز ۵) — Logical Audit (Coherence + Anti-pattern)
        scan_v5_coherence: Dict[str, Any] = {}
        scan_v5_anti_patterns: List[Dict[str, Any]] = []
        try:
            if getattr(watched, "logic_audit_enabled", True):
                write_progress(
                    watched_id, phase="phase5_logic_audit",
                    message="تحلیل منطقی coherence و anti-patterns",
                )
                from .scan_v5.coherence_analyzer import analyze_coherence
                from .scan_v5.anti_pattern_detector import detect_anti_patterns

                scan_v5_coherence = await analyze_coherence(
                    purpose_map=scan_v5_purpose_map,
                    inventory=scan_v5_inventory,
                    file_contents=deep_contents,
                    verify_model_id=(model_ids[0] if model_ids else model_id),
                )
                scan_v5_anti_patterns = await detect_anti_patterns(
                    file_contents=deep_contents,
                    inventory=scan_v5_inventory,
                    purpose_map=scan_v5_purpose_map,
                    verify_model_id=(model_ids[0] if model_ids else model_id),
                )
                logger.info(
                    f"scan_v5 logic_audit: "
                    f"coherence_issues={len(scan_v5_coherence.get('issues', []))}, "
                    f"anti_patterns={len(scan_v5_anti_patterns)}"
                )
                if scan_v5_session_id:
                    from .scan_v5.scan_inspector_session import log_scan_message
                    log_scan_message(
                        scan_v5_session_id, "system",
                        f"🧠 logic audit: "
                        f"{len(scan_v5_coherence.get('issues', []))} coherence + "
                        f"{len(scan_v5_anti_patterns)} anti-pattern",
                    )
        except Exception as _e_logic:
            logger.warning(f"scan_v5 logic_audit failed: {_e_logic}")

        # 🆕 (Phase 5 — فاز ۶) — Notification System Audit (R12)
        scan_v5_notif_audit: Dict[str, Any] = {"summary": {}}
        try:
            if getattr(watched, "notification_audit_enabled", True):
                write_progress(
                    watched_id, phase="phase5_notif_audit",
                    message="audit سیستم notification (R12)",
                )
                from .scan_v5.notification_auditor import audit_notifications
                scan_v5_notif_audit = await audit_notifications(
                    inventory=scan_v5_inventory,
                    purpose_map=scan_v5_purpose_map,
                    file_contents=deep_contents,
                    verify_model_id=(model_ids[0] if model_ids else model_id),
                )
                logger.info(
                    f"scan_v5 notif_audit: {scan_v5_notif_audit.get('summary')}"
                )
                if scan_v5_session_id:
                    from .scan_v5.scan_inspector_session import log_scan_message
                    log_scan_message(
                        scan_v5_session_id, "system",
                        f"🔔 notification audit: "
                        f"{scan_v5_notif_audit.get('summary', {}).get('total_issues', 0)} issue "
                        f"({scan_v5_notif_audit.get('summary', {}).get('total_calls', 0)} call total)",
                    )
        except Exception as _e_na:
            logger.warning(f"scan_v5 notification audit failed: {_e_na}")

        # 🆕 (Phase 5 — فاز ۳) — Delta Detection + Bidirectional Dependency
        scan_v5_delta: Dict[str, Any] = {"summary": {}}
        scan_v5_change_impact: List[Dict[str, Any]] = []
        scan_v5_upstream_impact: List[Dict[str, Any]] = []
        scan_v5_added_ripple: List[Dict[str, Any]] = []
        try:
            if getattr(watched, "delta_analysis_enabled", True):
                write_progress(
                    watched_id, phase="phase5_delta",
                    message="تشخیص تغییرات از scan قبلی",
                )
                from .scan_v5.delta_analyzer import build_current_state, compute_delta
                from .scan_v5.dependency_analyzer import (
                    build_bidirectional_deps, analyze_change_impact,
                    analyze_upstream_impact, analyze_added_files_ripple,
                )
                current_state = build_current_state(deep_contents)
                prev_state = getattr(watched, "prev_scan_state", None)
                scan_v5_delta = compute_delta(
                    prev_state=prev_state,
                    current_state=current_state,
                    file_contents=deep_contents,
                    prev_contents=None,  # هنوز محتوای prev ذخیره نمی‌کنیم
                )
                logger.info(f"scan_v5 delta summary: {scan_v5_delta.get('summary')}")

                # Bidirectional deps
                bi_deps = build_bidirectional_deps(imports, imported_by)

                # 🆕 (Phase 5 — bug 23) — Ripple limits depth-aware
                _depth_now = getattr(watched, "scan_depth", "deep") or "deep"
                _ripple_limit_map = {
                    "quick": 10, "standard": 20, "balanced": 20,
                    "deep": 30, "thorough": 45, "ultra": 60,
                }
                _ripple_max = _ripple_limit_map.get(_depth_now, 30)

                # Logical impact analysis (R7 + R10) — هر سه جهت
                if not scan_v5_delta.get("summary", {}).get("first_scan"):
                    _vm = (model_ids[0] if model_ids else model_id)
                    # ۱) Downstream — dependents در خطر
                    scan_v5_change_impact = await analyze_change_impact(
                        delta=scan_v5_delta,
                        deps=bi_deps,
                        purpose_map=scan_v5_purpose_map,
                        file_contents=deep_contents,
                        verify_model_id=_vm,
                        max_changed=_ripple_max,
                    )
                    logger.info(
                        f"scan_v5 change_impact (downstream): {len(scan_v5_change_impact)} impacts"
                    )

                    # 🆕 ۲) Upstream — deps در خطر
                    scan_v5_upstream_impact = await analyze_upstream_impact(
                        delta=scan_v5_delta,
                        deps=bi_deps,
                        purpose_map=scan_v5_purpose_map,
                        file_contents=deep_contents,
                        verify_model_id=_vm,
                        max_changed=_ripple_max,
                    )
                    logger.info(
                        f"scan_v5 upstream_impact: {len(scan_v5_upstream_impact)} impacts"
                    )

                    # 🆕 ۳) Added files — orphan + companion
                    scan_v5_added_ripple = await analyze_added_files_ripple(
                        delta=scan_v5_delta,
                        deps=bi_deps,
                        inventory=scan_v5_inventory,
                        file_contents=deep_contents,
                        verify_model_id=_vm,
                        max_added=_ripple_max,
                    )
                    logger.info(
                        f"scan_v5 added_ripple: {len(scan_v5_added_ripple)} findings"
                    )

                # ذخیره state فعلی برای scan بعدی
                # 🆕 (v2 audit H1 fix) — در حالت Inspector، scope محدود است
                # و prev_scan_state را نباید با snapshot ناقص آلوده کنیم،
                # چون delta detection برای scan دوره‌ای بعدی فکر می‌کند
                # فایل‌های زیادی حذف/تغییر یافته‌اند.
                if _output_target_session_id is None:
                    watched.prev_scan_state = current_state
        except Exception as _e_delta:
            logger.warning(f"scan_v5 delta failed: {_e_delta}")

        # ذخیره روی watched برای دسترسی فازهای بعدی + UI
        # 🆕 (v2 audit H1 fix) — این snapshot ها هم در حالت inspector
        # نباید کارت پروژه را با scope محدود آلوده کنند.
        if _output_target_session_id is None:
            try:
                watched.last_scan_inventory = scan_v5_inventory
                watched.last_scan_purpose_map = scan_v5_purpose_map
                watched.last_scan_at_v5 = now_iso()
                # ذخیره stale + docs + delta درون inventory برای سادگی
                scan_v5_inventory["_stale"] = scan_v5_stale
                scan_v5_inventory["_feature_docs"] = scan_v5_feature_docs
                scan_v5_inventory["_delta"] = scan_v5_delta
                scan_v5_inventory["_change_impact"] = scan_v5_change_impact
                scan_v5_inventory["_upstream_impact"] = scan_v5_upstream_impact
                scan_v5_inventory["_added_ripple"] = scan_v5_added_ripple
                scan_v5_inventory["_runtime_state"] = scan_v5_runtime_state
                scan_v5_inventory["_outcome_data"] = scan_v5_outcome_data
                scan_v5_inventory["_effectiveness_issues"] = scan_v5_effectiveness_issues
                scan_v5_inventory["_scan_session_id"] = scan_v5_session_id
                scan_v5_inventory["_coherence"] = scan_v5_coherence
                scan_v5_inventory["_anti_patterns"] = scan_v5_anti_patterns
                scan_v5_inventory["_notif_audit"] = scan_v5_notif_audit
            except Exception:
                pass

        # 🆕 (Phase 5 — bug 9 fix) — اکنون که همه ماژول‌های Phase 5 اجرا
        # شده و متغیرها populated هستند، Phase 5 findings → standard
        # تبدیل می‌شوند و سپس dedup هوشمند روی کل all_findings اجرا می‌شود.
        try:
            from .scan_v5._findings_to_tasks import phase5_findings_to_standard

            _phase5_findings = phase5_findings_to_standard(
                stale=scan_v5_stale,
                anti_patterns=scan_v5_anti_patterns,
                coherence_issues=(scan_v5_coherence.get("issues") or []),
                effectiveness_issues=scan_v5_effectiveness_issues,
                notification_audit=scan_v5_notif_audit,
                change_impact=scan_v5_change_impact,
                upstream_impact=scan_v5_upstream_impact,
                added_ripple=scan_v5_added_ripple,
                delta=scan_v5_delta,
                inventory=scan_v5_inventory,
            )
            if _phase5_findings:
                logger.info(
                    f"scan_v5: converted {len(_phase5_findings)} Phase 5 findings → standard"
                )
                all_findings.extend(_phase5_findings)
                if scan_v5_session_id:
                    from .scan_v5.scan_inspector_session import log_scan_message
                    log_scan_message(
                        scan_v5_session_id, "system",
                        f"📝 Phase 5 findings → tasks pipeline: "
                        f"{len(_phase5_findings)} finding added"
                    )
        except Exception as _e_p5conv:
            logger.warning(f"scan_v5 findings → standard conversion failed: {_e_p5conv}")

        unique = _merge_similar_findings(all_findings)

        file_health_map: Dict[str, Dict[str, Any]] = {}
        # ابتدا برای هر فایل deep-read شده، یک ورودی اولیه با score=100
        for path in deep_contents.keys():
            file_health_map[path] = {
                "score": 100.0,
                "findings_count": 0,
                "severity_weighted": 0.0,
                "passes_touched": [],
            }

        # حالا findings را پردازش کن
        for f in unique:
            target_files: List[str] = []
            # از target_locations اول، fallback به target_files
            for loc in (f.get("target_locations") or []):
                if isinstance(loc, dict) and loc.get("path"):
                    target_files.append(loc["path"])
            if not target_files:
                target_files = [p for p in (f.get("target_files") or []) if isinstance(p, str)]

            severity = (f.get("priority") or "medium").lower()
            pass_id = f.get("_pass", "quality")
            criteria_key = PASS_TO_CRITERIA.get(pass_id, "quality")
            weight = float(weights.get(criteria_key, 1.0))
            penalty = SEVERITY_PENALTY.get(severity, 5) * weight

            for path in target_files:
                if path not in file_health_map:
                    # فایل deep-read نشده — initialize کن
                    file_health_map[path] = {
                        "score": 100.0, "findings_count": 0,
                        "severity_weighted": 0.0, "passes_touched": [],
                    }
                fh = file_health_map[path]
                fh["score"] = max(0.0, fh["score"] - penalty)
                fh["findings_count"] = int(fh["findings_count"]) + 1
                fh["severity_weighted"] = float(fh["severity_weighted"]) + penalty
                if pass_id not in fh["passes_touched"]:
                    fh["passes_touched"].append(pass_id)

        # color/hex مشتق از score
        def _color_for_score(s: float) -> tuple:
            if s >= 70:
                return ("green", "#22C55E")
            elif s >= 40:
                return ("yellow", "#FBBF24")
            else:
                return ("red", "#EF4444")
        for path, fh in file_health_map.items():
            color, hex_code = _color_for_score(fh["score"])
            fh["color"] = color
            fh["hex"] = hex_code
            fh["score"] = round(fh["score"], 1)

        # محاسبهٔ overall_health_score (میانگین وزنی روی همه فایل‌ها)
        if file_health_map:
            overall_health_score = round(
                sum(fh["score"] for fh in file_health_map.values()) / len(file_health_map), 1
            )
        else:
            overall_health_score = 100.0
        # ذخیره در pass_summaries
        pass_summaries["health_summary"] = {
            "overall_health_score": overall_health_score,
            "files_analyzed_count": len(file_health_map),
            "red_files_count": sum(1 for fh in file_health_map.values() if fh["color"] == "red"),
            "yellow_files_count": sum(1 for fh in file_health_map.values() if fh["color"] == "yellow"),
            "green_files_count": sum(1 for fh in file_health_map.values() if fh["color"] == "green"),
            "criteria_weights_used": weights,
        }
        pass_summaries["file_health_map"] = file_health_map

        # 🆕 (inspector-scan) — تشخیص target output
        # اگر output_target نشان‌گر inspector session است، findings به
        # OversightTask تبدیل نمی‌شوند بلکه به proposal payload در همان
        # session chat لاگ می‌شوند. این از `_output_target_session_id` که
        # در ابتدای تابع pre-parse شد استفاده می‌کند.
        _inspector_session_id: Optional[int] = _output_target_session_id

        # ساخت تسک با پرامپت قوی غنی‌شده
        created_tasks: List[Dict[str, Any]] = []
        # 🆕 (inspector-scan) — لیست proposal payload ها (وقتی هدف Inspector است)
        proposal_payloads: List[Dict[str, Any]] = []
        # 🆕 (P2) آمار dedup: کدام task‌های موجود با finding‌های جدید match کردند
        duplicates_skipped: List[str] = []
        execution_mode_default = (watched.default_execution_mode or "manual")
        tech_context_default = (
            f"Stack: {', '.join(stacks)}." if stacks else ""
        )
        # 🆕 (Phase 5 — bug 6) — افزایش cap از 30 به 200 تا Phase 5 findings
        # (164 stale + 121 anti-pattern + 27 notification + ...) همه به task
        # تبدیل شوند. dedup قدیمی همچنان عمل می‌کند برای جلوگیری از تکرار.
        for f in unique[:200]:
            try:
                title = (f.get("title") or "").strip()[:200]
                if not title:
                    continue

                # === locations: ترجیح با target_locations جدید (dict) و fallback به target_files ===
                target_locations = f.get("target_locations") or []
                target_files: List[str] = list(f.get("target_files") or [])
                if not target_locations and target_files:
                    target_locations = [{"path": p} for p in target_files]
                if target_locations and not target_files:
                    target_files = [
                        l.get("path") for l in target_locations
                        if isinstance(l, dict) and l.get("path")
                    ]

                # === related_files: از پاسخ AI + غنی‌سازی از گراف import ===
                ai_related = f.get("related_files") or []
                if not isinstance(ai_related, list):
                    ai_related = []
                graph_related = _related_for_paths(
                    [p for p in target_files if p],
                    imports, imported_by, limit=6,
                )
                # ادغام بدون تکرار
                seen_related: set = set()
                merged_related: List[Dict[str, Any]] = []
                for r in ai_related + graph_related:
                    if isinstance(r, str):
                        r = {"path": r}
                    p = (r.get("path") or "").strip() if isinstance(r, dict) else ""
                    if p and p not in seen_related:
                        seen_related.add(p)
                        merged_related.append(r)

                # === acceptance criteria ===
                ac = f.get("acceptance_criteria") or [
                    "اعمال تغییر بدون شکستن تست‌های موجود",
                    "linter بدون warning عبور می‌کند",
                    "type-check موفق است",
                ]

                # === before/after examples ===
                examples = f.get("before_after_examples") or []
                if not isinstance(examples, list):
                    examples = []

                # === validation commands — اگر AI نداد، defaults بر اساس stack بساز ===
                vcmds = f.get("validation_commands") or []
                if not isinstance(vcmds, list):
                    vcmds = []
                if not vcmds:
                    if "fastapi" in stacks or "django" in stacks or "flask" in stacks:
                        vcmds.append("pytest")
                    if "nextjs" in stacks or "react" in stacks or "vue" in stacks:
                        vcmds.extend(["npm run build", "npm run lint"])

                full_prompt = build_strong_prompt(
                    title=title,
                    user_goal=watched.user_notes,
                    description=f.get("description", ""),
                    proposed_action=f.get("proposed_action", ""),
                    target_files=target_files,
                    target_locations=target_locations,
                    related_files=merged_related,
                    dependency_summary=(f.get("dependency_summary") or "").strip(),
                    tech_context=(f.get("tech_context") or tech_context_default),
                    before_after_examples=examples,
                    validation_commands=vcmds,
                    acceptance_criteria=ac,
                    risks=(f.get("risks") or "").strip(),
                    type_=f.get("type", "other"),
                    priority=f.get("priority", "medium"),
                    estimate=(f.get("estimated_complexity") or "medium"),
                )

                # 🆕 (inspector-scan) — اگر هدف یک session بازرس ویژه است،
                # به‌جای ساخت OversightTask، یک proposal payload بساز و
                # continue. **هیچ‌چیزی در DB ذخیره نمی‌شود.**
                if _inspector_session_id is not None:
                    proposal_payloads.append({
                        "proposal_id": str(uuid.uuid4()),
                        "title": title,
                        "type": f.get("type", "other"),
                        "priority": f.get("priority", "medium"),
                        "description": f.get("description", ""),
                        "proposed_action": f.get("proposed_action", ""),
                        "target_files": target_files,
                        "target_locations": target_locations,
                        "related_files": merged_related,
                        "acceptance_criteria": ac,
                        "validation_commands": vcmds,
                        "before_after_examples": examples,
                        "tech_context": (f.get("tech_context") or tech_context_default),
                        "dependency_summary": (f.get("dependency_summary") or "").strip(),
                        "risks": (f.get("risks") or "").strip(),
                        "estimated_complexity": (f.get("estimated_complexity") or "medium"),
                        "strong_prompt": full_prompt,
                        "execution_status": "pending",  # pending | applied_locally | committed | failed
                        "_pass": f.get("_pass", ""),
                    })
                    continue

                # 🆕 (P1) ضبط metadata scan که این task را ساخته
                task_scan_metadata = {
                    "model": model_id or (model_ids[0] if model_ids else "default"),
                    # 🔧 standardized نام (یکسان با last_scan_metadata)
                    "models_used_list": list(model_ids) if model_ids else ([model_id] if model_id else []),
                    "depth": getattr(watched, "scan_depth", "deep"),
                    "passes": passes_done,
                    "passes_total": len(PASSES),
                    "files_count": len(all_files),
                    "scan_id": read_progress(watched.id).get("started_at") or now_iso(),
                    "scanned_at": now_iso(),
                    "_pass": f.get("_pass", ""),
                }
                # 🆕 (Phase 5 — فاز ۸) — task_steps هوشمند برای auto-tasks
                # (R5: «حالت هوشمند که برای تولید چک‌لیست یا عدم تولیدش حسب نیاز»)
                # mode: auto = AI تصمیم می‌گیرد، always = همیشه، never = هرگز
                auto_task_steps: List[Dict[str, Any]] = []
                try:
                    checklist_mode = getattr(watched, "auto_task_checklist_mode", "auto") or "auto"
                    # heuristic پیچیدگی: scope طولانی + multiple AC + multiple target_files
                    complexity_score = (
                        (1 if len(ac) >= 4 else 0)
                        + (1 if len(target_files) >= 3 else 0)
                        + (1 if len(f.get("description", "")) > 500 else 0)
                    )
                    should_split = (
                        checklist_mode == "always"
                        or (checklist_mode == "auto" and complexity_score >= 2)
                    )
                    if should_split:
                        # full_prompt + raw_idea را به planner بده تا task_steps بسازد
                        auto_task_steps = await service._ai_plan_steps_from_idea(
                            idea=f.get("description", "") + "\n\n" + (full_prompt or "")[:3000],
                            user_goal=getattr(watched, "user_notes", "") or "",
                            model_id=(model_ids[0] if model_ids else model_id),
                            model_ids=None,
                        )
                        # normalize برای schema OversightTask.task_steps
                        for st in auto_task_steps:
                            st.setdefault("status", "pending")
                            st.setdefault("completion_pct", 0)
                except Exception as _ts_e:
                    logger.debug(f"auto task_steps generation skipped: {_ts_e}")

                t = OversightTask(
                    id=str(uuid.uuid4()),
                    watched_id=watched.id,
                    project_full_name=watched.repo_full_name,
                    title=title,
                    prompt=full_prompt,
                    raw_idea=f.get("description", ""),
                    type=f.get("type", "other"),
                    priority=f.get("priority", "medium"),
                    status="suggested",
                    source="auto_scan",
                    target_files=target_files,
                    acceptance_criteria=ac,
                    execution_mode=execution_mode_default,
                    # 🆕 (Phase 5 — فاز ۸) — checklist هوشمند برای auto-tasks
                    task_steps=auto_task_steps,
                    # 🆕 finding های ادغام‌شده در این task (از smart merger)
                    merged_findings=(f.get("merged_findings") or []),
                    # 🆕 (P1) metadata scan
                    created_by_scan_metadata=task_scan_metadata,
                    # 🆕 (P2) cross-scan tracking — اولین بار دیده شد
                    scan_seen_count=1,
                    last_seen_in_scan_at=now_iso(),
                )
                # 🆕 (P2) Cross-scan dedup: قبل از append، بررسی کن آیا
                # task مشابه active در همین watched وجود دارد
                existing = _find_existing_active_task(service, watched.id, f)
                if existing is not None:
                    # تسک تکراری → فقط counter را بالا ببر و metadata به‌روز کن
                    async with service._lock:
                        existing.scan_seen_count = (
                            getattr(existing, "scan_seen_count", 1) or 1
                        ) + 1
                        existing.last_seen_in_scan_at = now_iso()
                        # شواهد جدید scan را به raw_idea append کن (با حد طول)
                        new_evidence = (
                            f"\n---\n[scan #{existing.scan_seen_count} at {now_iso()}]\n"
                            f"{(f.get('description') or '')[:300]}"
                        )
                        if existing.raw_idea and len(existing.raw_idea) < 2000:
                            existing.raw_idea = (existing.raw_idea + new_evidence)[:3000]
                        existing.updated_at = now_iso()
                    duplicates_skipped.append(existing.id)
                    continue
                async with service._lock:
                    service.tasks.append(t)
                created_tasks.append(t.to_dict())
            except Exception as _e:
                logger.warning(f"deep_scan: building task failed: {_e}")
                continue

        # 🆕 (inspector-scan) — اگر در حالت inspector session هستیم، proposals
        # را به همان session لاگ کن. _save_tasks فراخوانی نمی‌شود چون هیچ
        # task جدیدی در service.tasks اضافه نشده.
        if _inspector_session_id is not None:
            # 🆕 (inspector-scoped-scan) — post-filter پیشنهادها بر اساس ربط
            # به focus_notes. حتی با pass-scoping، ممکنه LLM پیشنهاد بسازه
            # که به درخواست کاربر بی‌ربط باشه (مثلاً اسکن frontend بزنیم
            # ولی پیشنهاد بده برای backend هم refactor کن). با یک پاس
            # سریعِ relevance-scoring اون‌ها رو drop می‌کنیم.
            _dropped_irrelevant: List[Dict[str, Any]] = []
            try:
                _fn_for_filter = (focus_notes or "").strip()
                if _fn_for_filter and len(proposal_payloads) > 3:
                    proposal_payloads, _dropped_irrelevant = await _filter_proposals_by_relevance(
                        service,
                        proposals=proposal_payloads,
                        focus_notes=_fn_for_filter,
                        model_id=(model_ids[0] if model_ids else model_id),
                    )
                    if _dropped_irrelevant:
                        logger.info(
                            f"inspector-scoped-scan: dropped "
                            f"{len(_dropped_irrelevant)} irrelevant proposals "
                            f"(kept {len(proposal_payloads)})"
                        )
            except Exception as _filt_e:
                logger.warning(f"inspector-scoped-scan: relevance filter failed: {_filt_e}")

            try:
                from .scan_v5.scan_inspector_session import log_scan_message
                _ss = scan_scope_meta or {}
                _dropped_note = (
                    f" ({len(_dropped_irrelevant)} پیشنهاد بی‌ربط حذف شد)"
                    if _dropped_irrelevant else ""
                )
                summary_text = (
                    f"✅ اسکن موردی تمام شد — **{len(proposal_payloads)} پیشنهاد** "
                    f"از {len(unique)} finding استخراج شد{_dropped_note}. "
                    f"می‌توانید هر پیشنهاد را جداگانه «اجرا با AI» کنید یا "
                    f"«اعمال همهٔ تغییرات» را برای commit + push همه با هم بزنید."
                )
                _started_at_str = read_progress(watched_id).get("started_at") or now_iso()
                try:
                    _duration_ms = int(
                        (datetime.now(timezone.utc).timestamp()
                         - datetime.fromisoformat(_started_at_str.replace("Z", "+00:00")).timestamp())
                        * 1000
                    )
                except Exception:
                    _duration_ms = 0
                log_scan_message(
                    session_id=_inspector_session_id,
                    role="assistant",
                    content=summary_text,
                    action_type="scan_complete",
                    model_id=(model_ids[0] if model_ids else model_id),
                    extra_data={
                        "kind": "selective_scan_complete",
                        "scan_proposals": proposal_payloads,
                        "scope": {
                            "selected_sections": _ss.get("selected_sections") or [],
                            "custom_paths": _ss.get("custom_paths") or [],
                            "focus_notes": _ss.get("focus_notes"),
                            "include_dependencies": _ss.get("include_dependencies", True),
                            "scoped_files": _ss.get("after_filter") or _ss.get("scoped_files") or 0,
                            "deps_added": _ss.get("dependencies_added") or 0,
                        },
                        "summary": {
                            "total_proposals": len(proposal_payloads),
                            "findings_count": len(unique),
                            "passes_run": passes_done,
                            "scan_duration_ms": _duration_ms,
                        },
                    },
                )
            except Exception as _log_e:
                logger.warning(f"inspector-scan: logging proposals failed: {_log_e}")
            # در حالت inspector، tasks list دست‌نخورده مانده، پس _save_tasks
            # لازم نیست. ولی scan_results را روی disk بنویس (برای cache
            # بعدی /sections و progress)، و last_scan_at را به‌روز نکن
            # (چون این scan موردی است نه دوره‌ای).
        else:
            async with service._lock:
                service._save_tasks()

        # ذخیرهٔ نتیجهٔ خام scan
        try:
            _write_json(
                SCAN_RESULTS_DIR / f"{watched_id}.json",
                {
                    "watched_id": watched_id,
                    "repo": repo,
                    "ran_at": now_iso(),
                    "passes_run": passes_done,
                    "findings": unique,
                    "tasks_created": [t["id"] for t in created_tasks],
                    # 🆕 خلاصه‌های ساختاریافته از passes تخصصی
                    # (security_summary, coverage_summary, ...) برای UI
                    "pass_summaries": pass_summaries,
                },
            )
        except Exception:
            pass

        # به‌روزرسانی last_scan_at روی watched — فقط در حالت scan معمولی.
        # اسکن موردی Inspector نباید scheduler دوره‌ای را reset کند.
        if _inspector_session_id is None:
            watched.last_scan_at = now_iso()
            try:
                from datetime import timedelta
                watched.next_scan_at = (
                    datetime.now(timezone.utc) + timedelta(hours=watched.scan_interval_hours)
                ).isoformat()
            except Exception:
                pass
            async with service._lock:
                service._save_watched()

        # 🆕 (P1) metadata کامل scan برای نمایش در UI و notification
        # 🆕 (P3) per-pass breakdown
        pass_breakdown: Dict[str, int] = {}
        for finding in unique:
            pid = finding.get("_pass") or "?"
            pass_breakdown[pid] = pass_breakdown.get(pid, 0) + 1
        scan_metadata = {
            "model_used": model_id or (model_ids[0] if model_ids else "default"),
            "models_used_list": list(model_ids) if model_ids else ([model_id] if model_id else []),
            "scan_depth": getattr(watched, "scan_depth", "deep"),
            "passes_run": passes_done,
            "passes_total": len(PASSES),
            "files_analyzed_count": len(all_files),
            "scan_id": read_progress(watched_id).get("started_at") or now_iso(),
        }
        write_progress(
            watched_id,
            status="completed",
            phase="completed",
            message=f"اسکن کامل شد - {len(created_tasks)} تسک ساخته شد",
            findings_count=len(unique),
            tasks_created=len(created_tasks),
            critical_count=critical_count,
            completed_at=now_iso(),
            pass_breakdown=pass_breakdown,
            duplicates_skipped=len(duplicates_skipped),
            # 🆕 (selective-scan) — scope info را در progress ذخیره کن
            scope=scan_scope_meta,
            **scan_metadata,
        )

        # 🆕 (Phase 5 — bug 27) — بستن (archive) scan inspector session.
        # قبلاً sessions با status="active" باقی می‌ماندند و در archive list
        # تب «بازرس ویژه» دیده نمی‌شدند (UI فقط status=archived را می‌آورد).
        # نتیجه: کاربر فکر می‌کرد scan هیچ session ای نمی‌سازد، در حالی
        # که می‌ساخت اما هرگز finalize نمی‌شد و در archive ظاهر نمی‌شد.
        if scan_v5_session_id:
            try:
                from .scan_v5.scan_inspector_session import (
                    log_scan_message, archive_scan_session,
                )
                # یک پیام نهایی با خلاصه نتایج
                log_scan_message(
                    session_id=scan_v5_session_id,
                    role="system",
                    content=(
                        f"✅ Scan کامل شد\n\n"
                        f"📊 آمار:\n"
                        f"• {len(unique)} یافتهٔ منحصربه‌فرد\n"
                        f"• {len(created_tasks)} تسک جدید ساخته شد\n"
                        f"• {len(duplicates_skipped)} تسک تکراری (skip)\n"
                        f"• {critical_count} مورد critical\n"
                        f"• {passes_done}/{len(PASSES)} pass اجرا شد"
                    ),
                    action_type="scan_completed",
                )
                archive_scan_session(scan_v5_session_id)
                logger.info(
                    f"scan_inspector: session #{scan_v5_session_id} archived "
                    f"(found {len(unique)}, created {len(created_tasks)})"
                )
            except Exception as _e_arch:
                logger.warning(f"scan_inspector: archive failed: {_e_arch}")

        # 🆕 (P4) ذخیره خلاصهٔ آخرین scan روی خود WatchedProject — برای نمایش
        # دائمی در UI WatchedCard (مستقل از progress JSON که override می‌شود)
        # (audit fix I1) — در حالت Inspector scan موردی، metadata نباید
        # کارت پروژه را آلوده کند. این scan دوره‌ای نیست.
        if _inspector_session_id is None:
            try:
                async with service._lock:
                    watched.last_scan_metadata = {
                        **scan_metadata,
                        "findings_count": len(unique),
                        "tasks_created": len(created_tasks),
                        "duplicates_skipped": len(duplicates_skipped),
                        "critical_count": critical_count,
                        "completed_at": now_iso(),
                        "pass_breakdown": pass_breakdown,
                    }
                    service._save_watched()
            except Exception as _e:
                logger.debug(f"failed to save last_scan_metadata: {_e}")

        # 🔔 notification — silent skip اگر env تنظیم نشده باشد
        # (audit fix I3) — در حالت Inspector scan موردی، Telegram/PDF/notification
        # نباید fire شود. این scan ad-hoc از chat است نه دوره‌ای.
        # برای حداقل کردن تغییر indentation در یک بلوک ۲۰۰ خطی، از یک
        # exit-flag در ابتدای try استفاده می‌کنیم که در طول کل بلوک check
        # می‌شود. شایان ذکر است که existing except کلی همه را می‌گیرد.
        try:
            if _inspector_session_id is not None:
                # raise برای exit از این try (catch می‌شود توسط except پایین)
                raise _InspectorSkipPostScan()
            from .notification_service import notification_service
            watched_obj = next((w for w in service.watched if w.id == watched_id), None)
            repo_name = watched_obj.repo_full_name if watched_obj else watched_id

            # 1) همیشه scan_done را بفرست (با خلاصه + metadata)
            depth_used = getattr(watched_obj, "scan_depth", "deep") if watched_obj else "deep"
            models_label = (
                ", ".join(model_ids) if model_ids
                else (model_id or "default")
            )
            msg_lines = [
                f"🔬 *Deep Scan کامل شد*",
                f"📁 `{repo_name}`",
                f"🤖 مدل: `{models_label}`",
                f"🔍 depth: *{depth_used}*",
                f"📊 *{passes_done}/{len(PASSES)}* pass اجرا شد",
                f"📑 *{len(all_files)}* فایل بررسی شد",
                f"🔎 *{len(unique)}* یافتهٔ منحصربه‌فرد",
                f"📝 *{len(created_tasks)}* تسک جدید ساخته شد",
            ]
            # 🆕 (P2) آمار dedup
            if duplicates_skipped:
                msg_lines.append(
                    f"🔁 *{len(duplicates_skipped)}* تسک تکراری skip شد (موجود به‌روز شد)"
                )
            if critical_count:
                msg_lines.append(f"🚨 *{critical_count}* مورد critical")
            # 🆕 (P3) per-pass breakdown از findings
            try:
                pass_counts: Dict[str, int] = {}
                for finding in unique:
                    pid = finding.get("_pass") or "?"
                    pass_counts[pid] = pass_counts.get(pid, 0) + 1
                if pass_counts:
                    breakdown = " · ".join(f"{p}:{n}" for p, n in sorted(
                        pass_counts.items(), key=lambda x: -x[1]
                    )[:6])
                    msg_lines.append(f"📊 per-pass: {breakdown}")
            except Exception:
                pass
            # 🆕 (Phase 5 — فاز ۸) — Telegram template جامع برای scan_completed
            # شامل: tasks count + delta + logic + notification audit + inspector link
            try:
                _v5_summary = (scan_v5_inventory.get("_meta") or {}).get("counts", {})
                _v5_stale_summary = (scan_v5_stale.get("summary") or {})
                _v5_delta_summary = (scan_v5_delta.get("summary") or {})
                _v5_coh_count = len((scan_v5_coherence.get("issues") or []))
                _v5_ap_count = len(scan_v5_anti_patterns)
                _v5_notif_issues = (scan_v5_notif_audit.get("summary") or {}).get("total_issues", 0)
                _v5_eff_count = len(scan_v5_effectiveness_issues)
                _v5_change_impact_count = len(scan_v5_change_impact)
                msg_lines.append("")
                msg_lines.append("🔬 *Phase 5 (scan v5)*:")
                if _v5_summary:
                    msg_lines.append(
                        f"  📋 inventory: "
                        f"endpoints={_v5_summary.get('backend_endpoints', 0)}, "
                        f"ui={_v5_summary.get('ui_elements', 0)}, "
                        f"notifications={_v5_summary.get('notification_calls', 0)}"
                    )
                if _v5_stale_summary.get("structural_total", 0) or _v5_stale_summary.get("semantic_total", 0):
                    msg_lines.append(
                        f"  🗑 stale: "
                        f"{_v5_stale_summary.get('structural_total', 0)} structural + "
                        f"{_v5_stale_summary.get('semantic_total', 0)} semantic"
                    )
                if _v5_delta_summary and not _v5_delta_summary.get("first_scan", True):
                    msg_lines.append(
                        f"  🔄 delta: "
                        f"add={_v5_delta_summary.get('add', 0)}, "
                        f"remove={_v5_delta_summary.get('remove', 0)}, "
                        f"modify={_v5_delta_summary.get('modify', 0)}, "
                        f"signature_change={_v5_delta_summary.get('signature_change', 0)}"
                    )
                if _v5_change_impact_count:
                    msg_lines.append(f"  ⚠️ {_v5_change_impact_count} dependent در خطر تغییر (downstream)")
                # 🆕 (bug 23) — upstream + ripple counts
                _v5_upstream_count = len(scan_v5_upstream_impact or [])
                _v5_ripple_count = len(scan_v5_added_ripple or [])
                if _v5_upstream_count:
                    msg_lines.append(f"  ⬆️ {_v5_upstream_count} upstream در خطر (نیاز update)")
                if _v5_ripple_count:
                    msg_lines.append(f"  🧩 {_v5_ripple_count} added-file ripple (orphan/companion)")
                if _v5_coh_count or _v5_ap_count:
                    msg_lines.append(
                        f"  🧠 logic: {_v5_coh_count} coherence + {_v5_ap_count} anti-pattern"
                    )
                if _v5_eff_count:
                    msg_lines.append(f"  📊 effectiveness: {_v5_eff_count} issue (outcome-based)")
                if _v5_notif_issues:
                    msg_lines.append(f"  🔔 notification audit: {_v5_notif_issues} issue")
                if scan_v5_session_id:
                    msg_lines.append(f"  🔍 inspector session: #{scan_v5_session_id}")
            except Exception as _v5_msg_e:
                logger.debug(f"scan_v5 message enrichment failed: {_v5_msg_e}")

            # 🆕 (Phase 5 — bug 13) — Top N task list برای Telegram
            # هر تسک ۱-۲ خط: priority + type + title (پیامد۱۲۰ کاراکتر) + AC count.
            # پرامپت کامل در PDF bundle attached می‌ماند.
            try:
                if created_tasks:
                    PRIO = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                    _sorted = sorted(
                        created_tasks,
                        key=lambda x: PRIO.get(
                            (x.get("priority") or "medium").lower(), 2
                        ),
                    )
                    TOP_N = 15
                    msg_lines.append("")
                    msg_lines.append(
                        f"📝 *Top {min(TOP_N, len(_sorted))} تسک* "
                        f"(از {len(_sorted)} کل — پرامپت کامل در PDF):"
                    )
                    PRIO_EMOJI = {
                        "critical": "🚨",
                        "high": "🔴",
                        "medium": "🟡",
                        "low": "🟢",
                    }
                    for t in _sorted[:TOP_N]:
                        pr = (t.get("priority") or "medium").lower()
                        emoji = PRIO_EMOJI.get(pr, "•")
                        type_short = (t.get("type") or "?")[:18]
                        tl = (t.get("title") or "?")
                        if len(tl) > 100:
                            tl = tl[:97] + "..."
                        ac_count = len(t.get("acceptance_criteria") or [])
                        msg_lines.append(
                            f"  {emoji} `{type_short}` · {tl} _(AC: {ac_count})_"
                        )
                    if len(_sorted) > TOP_N:
                        msg_lines.append(
                            f"  _... و {len(_sorted) - TOP_N} تسک دیگر در PDF._"
                        )
            except Exception as _tlist_e:
                logger.debug(f"telegram task list failed: {_tlist_e}")

            done_priority = "high" if critical_count > 0 else ("medium" if len(created_tasks) > 0 else "low")
            # 🆕 (R6) silent default = NOT bool(watched.scan_notify_sound)
            _silent_default = not bool(getattr(watched, "scan_notify_sound", False))

            # 🆕 (Phase 5 — bug 2 fix) — scan-bundle PDF attachment
            _scan_bundle_attachment: Optional[Dict[str, Any]] = None
            try:
                from .scan_v5.scan_bundle import build_scan_bundle_pdf
                _bundle_bytes, _bundle_ext = await build_scan_bundle_pdf(
                    watched=watched,
                    scan_v5_inventory=scan_v5_inventory,
                    created_tasks=created_tasks,
                    all_findings=all_findings,
                )
                # ذخیره روی disk تا notification_service بتواند ضمیمه کند
                from pathlib import Path as _PA
                _bundle_dir = _PA("storage/scan_v5_bundles")
                _bundle_dir.mkdir(parents=True, exist_ok=True)
                _bundle_name = (
                    f"scan_bundle_{watched_id}_{uuid.uuid4().hex[:8]}{_bundle_ext}"
                )
                _bundle_path = _bundle_dir / _bundle_name
                _bundle_path.write_bytes(_bundle_bytes)
                _scan_bundle_attachment = {
                    "bytes": _bundle_bytes,
                    "filename": _bundle_name,
                    "path": str(_bundle_path),
                }
                logger.info(
                    f"scan_v5 bundle generated: {_bundle_path} "
                    f"({len(_bundle_bytes)} bytes, ext={_bundle_ext})"
                )
                if scan_v5_session_id:
                    from .scan_v5.scan_inspector_session import log_scan_message
                    log_scan_message(
                        scan_v5_session_id, "system",
                        f"📦 scan bundle ساخته شد ({_bundle_ext}, "
                        f"{len(_bundle_bytes) // 1024}KB)",
                    )
            except Exception as _e_bun:
                logger.warning(f"scan_v5 bundle generation failed: {_e_bun}")

            await notification_service.notify_event(
                "scan_done", "\n".join(msg_lines),
                subject="Deep Scan completed",
                priority=done_priority,
                project_name=repo_name,
                watched_id=watched_id,
                silent=_silent_default,
                attachment=_scan_bundle_attachment,
            )

            # 2) اگر یافتهٔ critical داشت، یک پیام جداگانه با priority بالا
            if critical_count > 0:
                crit_msg = (
                    f"🚨 *{critical_count} مورد critical* در اسکن `{repo_name}` پیدا شد!\n"
                    f"به پنل تسک‌ها مراجعه کنید."
                )
                await notification_service.notify_event(
                    "scan_critical_found", crit_msg,
                    subject=f"🚨 {critical_count} critical finding",
                    priority="critical",
                    project_name=repo_name,
                    watched_id=watched_id,
                )
        except Exception as e:
            logger.debug(f"scan notification skipped: {e}")

        return {
            "success": True,
            "files_count": len(all_files),
            "stacks": stacks,
            "passes_run": passes_done,
            "findings": len(unique),
            "tasks_created": len(created_tasks),
            "task_ids": [t["id"] for t in created_tasks],
            # 🆕 (P2) آمار dedup
            "duplicates_skipped": len(duplicates_skipped),
            "duplicate_task_ids": list(duplicates_skipped),
        }
