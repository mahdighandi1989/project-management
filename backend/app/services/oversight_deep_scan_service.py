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
    r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))",
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
            for m in _PY_IMPORT_RE.finditer(content):
                mod = m.group(1) or m.group(2) or ""
                if mod.startswith("."):
                    # relative import — best-effort skip (rare in this codebase)
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


def _score_files(
    paths: List[str],
    sizes: Dict[str, int],
    recent_changed_files: List[str],
    import_counts: Dict[str, int],
) -> List[Tuple[str, int]]:
    """ترتیب فایل‌ها بر اساس امتیاز اهمیت برای deep-read."""
    scores: Dict[str, int] = {}
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
]


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

        # Phase 2: ابتدا rank سبک، سپس rerank با import graph
        ranked0 = _score_files(all_files, sizes, [], {})
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
        ranked = _score_files(all_files, sizes, [], real_import_counts)
        final_paths = [p for p, s in ranked[: max_deep_read] if s > 0]
        for p in final_paths:
            if p not in deep_contents:
                try:
                    c = await _fetch_file_content(session, repo_full_name, p, headers, active_branch, max_file_bytes)
                    if c:
                        deep_contents[p] = c
                except Exception:
                    continue

        # Special context: README، CHANGELOG، tsconfig، next.config، ...
        special_files = [
            f for f in all_files
            if f.split("/")[-1].lower() in ("readme.md", "readme", "changelog.md")
            or f.startswith(("docs/", "documentation/"))
            or f in ("tsconfig.json", "next.config.js", "next.config.mjs", "vite.config.ts", ".env.example")
        ][:6]
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
        deep_files_blob = "\n\n".join(
            f"=== {p} ===\n{_with_line_numbers(c, max_file_lines)}"
            for p, c in list(deep_contents.items())[:max_deep_read]
        )
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
            sim = _title_similarity(title, u_title)

            # شرط ۱: exact match (sim=1.0)
            if sim >= 1.0:
                merged_into = u
                break

            # شرط ۲: similarity بالا و type یکسان
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
# Main deep scan function
# =====================================================================

async def run_deep_scan(
    watched_id: str,
    *,
    model_id: Optional[str] = None,
    enabled_passes: Optional[List[str]] = None,
    deep_read_count: int = 35,
) -> Dict[str, Any]:
    """اجرای کامل deep scan روی یک watched."""
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise ValueError("پروژه یافت نشد")

    # 🆕 Mapping scan_depth → enabled_passes (مهاجرت از Health depth)
    # اگر enabled_passes صریحاً پاس داده شده، آن را استفاده کن
    # وگرنه از watched.scan_depth بخوان
    if enabled_passes is None:
        depth = getattr(watched, "scan_depth", "deep") or "deep"
        if depth == "quick":
            # سریع: فقط ۳ pass essential
            enabled_passes = ["frontend", "backend", "security_deep"]
        elif depth == "standard":
            # متعادل: ۵ pass
            enabled_passes = ["frontend", "backend", "security_deep",
                              "quality", "completeness"]
        elif depth == "thorough":
            # کامل + per-file scoring + roadmap (همه)
            enabled_passes = [p[0] for p in PASSES]
        else:  # "deep" (default)
            # عمیق: همه passes
            enabled_passes = [p[0] for p in PASSES]

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
        structure = {
            "watched_id": watched_id,
            "repo": repo,
            "branch": branch,
            "scanned_at": now_iso(),
            "files_count": len(all_files),
            "stacks": stacks,
            "kinds": kinds,
            "files": all_files[:2000],  # حداکثر ۲۰۰۰ مسیر
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
        # ابتدا یک sweep سبک: top-N اولیه را با نوع/حجم/critical path رتبه‌بندی کن
        ranked0 = _score_files(all_files, sizes, recent_changed, {})
        initial_deep_paths = [p for p, s in ranked0[: max(deep_read_count, 5) * 2] if s > 0]

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
            prompt = _build_pass_prompt(
                pass_id,
                repo=repo,
                user_goal=watched.user_notes or "",
                stacks=stacks,
                files_summary=files_summary,
                deep_files_blob=deep_files_blob,
                package_files_blob=package_files_blob,
                import_graph_summary=import_graph_summary,
            )
            try:
                response = await service._ai_generate(
                    prompt, model_id=model_id, max_tokens=4500, temperature=0.2
                )
                parsed = service._extract_json(response) or {}
                findings = parsed.get("findings") or []
                for f in findings:
                    f["_pass"] = pass_id
                    if f.get("priority") == "critical":
                        critical_count += 1
                all_findings.extend(findings)
                # 🆕 ذخیرهٔ summaries ساختاریافته از هر pass (security_summary,
                # coverage_summary, ...) — برای UI بدون reparsing findings
                for sum_key in ("security_summary", "coverage_summary"):
                    if isinstance(parsed.get(sum_key), dict):
                        pass_summaries[sum_key] = parsed[sum_key]
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
        unique = _merge_similar_findings(all_findings)

        # ----- فاز ۴.۵: محاسبهٔ per-file health map -----
        # (مهاجرت از Health analysis file_health_map)
        # برای هر فایل deep-read شده، یک score 0-100 محاسبه می‌شود بر اساس:
        #   - تعداد findings مرتبط (severity weighted)
        #   - وزن‌های کاربر (scan_criteria_weights)
        # خروجی در structure ذخیره می‌شود تا UI heatmap نمایش دهد.
        weights = getattr(watched, "scan_criteria_weights", None) or {
            "security": 1.5, "quality": 1.0, "tests": 1.2, "completeness": 1.0,
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
        }

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

        # ساخت تسک با پرامپت قوی غنی‌شده
        created_tasks: List[Dict[str, Any]] = []
        execution_mode_default = (watched.default_execution_mode or "manual")
        tech_context_default = (
            f"Stack: {', '.join(stacks)}." if stacks else ""
        )
        for f in unique[:30]:
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
                    # 🆕 finding های ادغام‌شده در این task (از smart merger)
                    merged_findings=(f.get("merged_findings") or []),
                )
                async with service._lock:
                    service.tasks.append(t)
                created_tasks.append(t.to_dict())
            except Exception as _e:
                logger.warning(f"deep_scan: building task failed: {_e}")
                continue

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

        # به‌روزرسانی last_scan_at روی watched
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

        write_progress(
            watched_id,
            status="completed",
            phase="completed",
            message=f"اسکن کامل شد - {len(created_tasks)} تسک ساخته شد",
            findings_count=len(unique),
            tasks_created=len(created_tasks),
            critical_count=critical_count,
            completed_at=now_iso(),
        )

        # 🔔 notification — silent skip اگر env تنظیم نشده باشد
        try:
            from .notification_service import notification_service
            watched_obj = next((w for w in service.watched_projects if w.id == watched_id), None)
            repo_name = watched_obj.repo_full_name if watched_obj else watched_id

            # 1) همیشه scan_done را بفرست (با خلاصه)
            msg_lines = [
                f"🔬 *Deep Scan کامل شد*",
                f"📁 `{repo_name}`",
                f"📊 *{passes_done}* pass اجرا شد",
                f"📑 *{len(all_files)}* فایل بررسی شد",
                f"🔎 *{len(unique)}* یافتهٔ منحصربه‌فرد",
                f"📝 *{len(created_tasks)}* تسک جدید ساخته شد",
            ]
            if critical_count:
                msg_lines.append(f"🚨 *{critical_count}* مورد critical")
            done_priority = "high" if critical_count > 0 else ("medium" if len(created_tasks) > 0 else "low")
            await notification_service.notify_event(
                "scan_done", "\n".join(msg_lines),
                subject="Deep Scan completed",
                priority=done_priority,
                project_name=repo_name,
                watched_id=watched_id,
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
        }
