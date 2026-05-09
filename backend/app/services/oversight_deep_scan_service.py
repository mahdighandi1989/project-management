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
    extra: str = "",
) -> str:
    base = f"""تو یک تحلیلگر senior software هستی. این یک فاز از یک اسکن چندفازی روی پروژهٔ زیر است.

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

# پروژه
{repo}
Stack تشخیص داده شده: {', '.join(stacks) or '(نامشخص)'}

# فایل‌ها (نمونه)
{files_summary}

# محتوای فایل‌های کلیدی
{deep_files_blob}

# فایل‌های Dependency
{package_files_blob}
"""

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
    }

    output = """
# خروجی فقط JSON (بدون متن اضافی، بدون ```)
{
  "findings": [
    {
      "title": "عنوان کوتاه",
      "type": "bug | refactor | docs | feature_request | security | other",
      "priority": "low | medium | high | critical",
      "description": "پاراگراف کامل توضیح",
      "proposed_action": "پیشنهاد عملی برای رفع",
      "target_files": ["path/to/file1", "path/to/file2"],
      "acceptance_criteria": ["معیار تستی ۱", "معیار تستی ۲"]
    }
  ]
}
حداکثر ۸ یافتهٔ مهم. تمرکز روی فاز فعلی باشد.
"""
    return base + (pass_specs.get(pass_id, "") + extra) + output


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

    enabled = set(enabled_passes or [p[0] for p in PASSES])

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
        # تخمین ساده‌ای از import_counts: فایل‌هایی که نام‌شان در سایر فایل‌ها زیاد به‌عنوان import می‌آید
        # اینجا برای صرفه‌جویی، صفر گذاشته می‌شود؛ scoring همچنان روی نوع/حجم/critical path کار می‌کند
        import_counts: Dict[str, int] = {}
        ranked = _score_files(all_files, sizes, recent_changed, import_counts)
        deep_paths = [p for p, s in ranked[: max(deep_read_count, 5)] if s > 0]

        deep_contents: Dict[str, str] = {}
        for i, p in enumerate(deep_paths):
            write_progress(
                watched_id,
                phase="phase2_reading",
                message=f"خواندن فایل‌های کلیدی ({i + 1}/{len(deep_paths)})",
                files_analyzed=i + 1,
            )
            try:
                c = await _fetch_file_content(session, repo, p, headers, branch, 50000)
                if c:
                    deep_contents[p] = c
            except Exception:
                continue

        # ساخت context
        files_summary = "\n".join(
            f"{kinds.get(p, 'other'):>10}  {p}" for p in all_files[:200]
        )
        deep_files_blob = "\n\n".join(
            f"=== {p} ===\n{c[:8000]}" for p, c in list(deep_contents.items())[:25]
        )
        package_files_blob = "\n\n".join(
            f"=== {n} ===\n{c[:3000]}" for n, c in dep_contents.items()
        )

        # ----- فاز ۳ -----
        all_findings: List[Dict[str, Any]] = []
        passes_done = 0
        critical_count = 0

        for pass_id, pass_label in PASSES:
            if pass_id not in enabled:
                continue
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
            )
            try:
                response = await service._ai_generate(
                    prompt, model_id=model_id, max_tokens=3000, temperature=0.2
                )
                parsed = service._extract_json(response) or {}
                findings = parsed.get("findings") or []
                for f in findings:
                    f["_pass"] = pass_id
                    if f.get("priority") == "critical":
                        critical_count += 1
                all_findings.extend(findings)
                write_progress(
                    watched_id,
                    findings_count=len(all_findings),
                    critical_count=critical_count,
                )
            except Exception as e:
                logger.warning(f"deep_scan pass {pass_id} failed: {e}")

            passes_done += 1
            write_progress(watched_id, passes_done=passes_done)

        # ----- فاز ۴: تجمیع، dedup، اولویت‌بندی -----
        write_progress(watched_id, phase="phase4_aggregate", message="dedup و اولویت‌بندی")
        unique: List[Dict[str, Any]] = []
        seen_titles: set = set()
        for f in all_findings:
            t = (f.get("title") or "").strip().lower()
            if not t or t in seen_titles:
                continue
            seen_titles.add(t)
            unique.append(f)

        # ساخت تسک با پرامپت قوی
        created_tasks: List[Dict[str, Any]] = []
        execution_mode_default = (watched.default_execution_mode or "manual")
        for f in unique[:30]:
            try:
                title = (f.get("title") or "").strip()[:200]
                if not title:
                    continue
                target_files = f.get("target_files") or []
                ac = f.get("acceptance_criteria") or [
                    "اعمال تغییر بدون شکستن تست‌های موجود",
                    "linter بدون warning عبور می‌کند",
                    "type-check موفق است",
                ]
                full_prompt = build_strong_prompt(
                    title=title,
                    user_goal=watched.user_notes,
                    description=f.get("description", ""),
                    proposed_action=f.get("proposed_action", ""),
                    target_files=target_files,
                    acceptance_criteria=ac,
                    type_=f.get("type", "other"),
                    priority=f.get("priority", "medium"),
                    estimate="medium",
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
                )
                async with service._lock:
                    service.tasks.append(t)
                created_tasks.append(t.to_dict())
            except Exception:
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

        return {
            "success": True,
            "files_count": len(all_files),
            "stacks": stacks,
            "passes_run": passes_done,
            "findings": len(unique),
            "tasks_created": len(created_tasks),
            "task_ids": [t["id"] for t in created_tasks],
        }
