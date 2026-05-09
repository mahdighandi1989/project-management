"""
Oversight Service
=================
سرویس مرکز نظارت و مدیریت پروژه‌های گیت‌هاب

- ذخیره‌سازی JSON-based در backend/storage/oversight/
- یکپارچگی با AI Manager موجود
- استفاده از توکن GitHub ذخیره‌شده در محیط/Setting

این سرویس عمداً ساده و مستقل نگه داشته شده تا کاربر بتواند بعداً
مدل‌های SQLAlchemy جداگانه‌ای بسازد بدون شکستن داده‌های موجود.
"""

from __future__ import annotations

import os
import json
import uuid
import asyncio
import logging
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import aiohttp

logger = logging.getLogger(__name__)

# ====================================================================
# مسیرها
# ====================================================================

STORAGE_DIR = Path(os.environ.get("OVERSIGHT_STORAGE", "./storage/oversight"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

WATCHED_FILE = STORAGE_DIR / "watched_projects.json"
TASKS_FILE = STORAGE_DIR / "tasks.json"
REPORTS_FILE = STORAGE_DIR / "reports.json"
SETTINGS_FILE = STORAGE_DIR / "settings.json"

GITHUB_API = "https://api.github.com"


# ====================================================================
# Helper: دسترسی به توکن
# ====================================================================

def get_github_token() -> str:
    """دریافت توکن گیت‌هاب از env یا دیتابیس."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token

    # تلاش از دیتابیس
    try:
        from ..core.database import SessionLocal
        from ..models.setting import Setting

        db = SessionLocal()
        try:
            for key in ("api_key_github", "github_token", "GITHUB_TOKEN"):
                value = Setting.get_value(db, key)
                if value:
                    os.environ["GITHUB_TOKEN"] = value
                    return value
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Couldn't read github token from DB: {e}")

    return ""


def get_render_token() -> str:
    """دریافت توکن Render از env یا دیتابیس."""
    token = os.environ.get("RENDER_API_KEY", "").strip()
    if token:
        return token
    try:
        from ..core.database import SessionLocal
        from ..models.setting import Setting

        db = SessionLocal()
        try:
            for key in ("api_key_render", "render_api_key", "RENDER_API_KEY"):
                value = Setting.get_value(db, key)
                if value:
                    os.environ["RENDER_API_KEY"] = value
                    return value
        finally:
            db.close()
    except Exception:
        pass
    return ""


# ====================================================================
# Data classes
# ====================================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WatchedProject:
    id: str
    repo_full_name: str
    repo_url: str
    private: bool = False
    default_branch: str = "main"
    language: str = ""
    user_notes: str = ""
    tags: List[str] = field(default_factory=list)
    schedule_enabled: bool = False
    interval_hours: float = 24.0
    autonomy_level: str = "manual"  # manual | assist | auto
    allow_push: bool = False  # opt-in جداگانه
    allow_create_issue: bool = False  # اجازه ساخت issue حتی در manual
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_scan_at: Optional[str] = None
    scan_interval_hours: float = 168.0  # هفتگی
    next_scan_at: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OversightTask:
    id: str
    watched_id: Optional[str]
    project_full_name: str
    title: str
    prompt: str
    raw_idea: str = ""
    type: str = "other"  # idea | bug | feature_request | refactor | docs | other
    priority: str = "medium"  # low | medium | high | critical
    status: str = "pending"  # pending | running | awaiting_review | done | failed | cancelled | suggested
    models_used: List[str] = field(default_factory=list)
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    runs_count: int = 0
    last_summary: str = ""
    deadline: Optional[str] = None
    source: str = "user"  # user | auto_scan
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OversightReport:
    id: str
    task_id: str
    watched_id: Optional[str]
    project_full_name: str
    run_at: str
    status: str  # done | partial | not_done | error
    done_parts: List[str] = field(default_factory=list)
    remaining_parts: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    next_actions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    raw_response: str = ""
    model_id: str = ""
    read: bool = False
    flagged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ====================================================================
# Persistence helpers
# ====================================================================

def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
        return default


def _write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(path)


# ====================================================================
# Service
# ====================================================================

class OversightService:
    """سرویس اصلی نظارت."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._session: Optional[aiohttp.ClientSession] = None

        # cache در حافظه
        self.watched: List[WatchedProject] = []
        self.tasks: List[OversightTask] = []
        self.reports: List[OversightReport] = []
        self.settings: Dict[str, Any] = {
            "default_models": [],
            "allow_auto_push_global": False,
            "max_parallel_runs": 2,
            "scan_interval_hours": 24,
        }

        self._load_all()

    # ---------- بارگذاری/ذخیره ----------

    @staticmethod
    def _filter_known_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """فیلتر کردن دادهٔ ذخیره‌شده تا فقط فیلدهای موجود در dataclass باقی بماند (سازگاری رو به جلو)."""
        from dataclasses import fields as _fields

        allowed = {f.name for f in _fields(cls)}
        return {k: v for k, v in data.items() if k in allowed}

    def _load_all(self) -> None:
        for w in _read_json(WATCHED_FILE, []):
            try:
                self.watched.append(WatchedProject(**self._filter_known_fields(WatchedProject, w)))
            except (TypeError, KeyError):
                logger.warning(f"Ignoring malformed watched entry: {w}")

        for t in _read_json(TASKS_FILE, []):
            try:
                self.tasks.append(OversightTask(**self._filter_known_fields(OversightTask, t)))
            except (TypeError, KeyError):
                logger.warning(f"Ignoring malformed task: {t}")

        for r in _read_json(REPORTS_FILE, []):
            try:
                self.reports.append(OversightReport(**self._filter_known_fields(OversightReport, r)))
            except (TypeError, KeyError):
                logger.warning(f"Ignoring malformed report: {r}")

        saved_settings = _read_json(SETTINGS_FILE, {})
        if isinstance(saved_settings, dict):
            self.settings.update(saved_settings)

    def _save_watched(self) -> None:
        _write_json(WATCHED_FILE, [w.to_dict() for w in self.watched])

    def _save_tasks(self) -> None:
        _write_json(TASKS_FILE, [t.to_dict() for t in self.tasks])

    def _save_reports(self) -> None:
        _write_json(REPORTS_FILE, [r.to_dict() for r in self.reports])

    def _save_settings(self) -> None:
        _write_json(SETTINGS_FILE, self.settings)

    # ---------- HTTP session ----------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _gh_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-debate-oversight/1.0",
        }
        eff = (token or get_github_token()).strip()
        if eff:
            headers["Authorization"] = f"Bearer {eff}"
        return headers

    # ====================================================================
    # GitHub: لیست repos کاربر
    # ====================================================================

    async def list_user_repos(self, max_pages: int = 5) -> Dict[str, Any]:
        """دریافت repos کاربر (شامل private)."""
        token = get_github_token()
        if not token:
            return {
                "success": False,
                "error": "توکن گیت‌هاب تنظیم نشده است. از صفحه تنظیمات وارد کنید.",
                "repos": [],
            }

        session = await self._get_session()
        headers = self._gh_headers(token)

        all_repos: List[Dict[str, Any]] = []
        per_page = 100
        try:
            for page in range(1, max_pages + 1):
                url = (
                    f"{GITHUB_API}/user/repos?per_page={per_page}"
                    f"&page={page}&sort=pushed&affiliation=owner,collaborator,organization_member"
                )
                async with session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status == 401:
                        return {
                            "success": False,
                            "error": "توکن گیت‌هاب نامعتبر است.",
                            "repos": [],
                        }
                    if resp.status != 200:
                        text = await resp.text()
                        return {
                            "success": False,
                            "error": f"خطای GitHub ({resp.status}): {text[:200]}",
                            "repos": [],
                        }
                    data = await resp.json()
                    if not isinstance(data, list) or not data:
                        break

                    for r in data:
                        all_repos.append(
                            {
                                "id": r.get("id"),
                                "full_name": r.get("full_name"),
                                "name": r.get("name"),
                                "owner": r.get("owner", {}).get("login"),
                                "description": r.get("description") or "",
                                "private": r.get("private", False),
                                "default_branch": r.get("default_branch", "main"),
                                "language": r.get("language") or "",
                                "html_url": r.get("html_url"),
                                "pushed_at": r.get("pushed_at"),
                                "updated_at": r.get("updated_at"),
                                "stargazers_count": r.get("stargazers_count", 0),
                                "forks_count": r.get("forks_count", 0),
                                "open_issues_count": r.get("open_issues_count", 0),
                                "topics": r.get("topics", []),
                                "archived": r.get("archived", False),
                            }
                        )

                    if len(data) < per_page:
                        break
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout در ارتباط با GitHub", "repos": all_repos}
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"خطای شبکه: {str(e)}", "repos": all_repos}

        return {
            "success": True,
            "repos": all_repos,
            "count": len(all_repos),
            "synced_at": now_iso(),
        }

    # ====================================================================
    # Project context for AI
    # ====================================================================

    async def _fetch_text(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        session = await self._get_session()
        try:
            async with session.get(url, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    return None
                return await resp.text()
        except Exception:
            return None

    async def _fetch_json(self, url: str, headers: Dict[str, str]) -> Any:
        session = await self._get_session()
        try:
            async with session.get(url, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except Exception:
            return None

    async def build_project_context(
        self,
        repo_full_name: str,
        branch: Optional[str] = None,
        max_tree: int = 80,
    ) -> Dict[str, Any]:
        """ساختن context پروژه برای AI."""
        token = get_github_token()
        headers = self._gh_headers(token)

        owner, _, repo = repo_full_name.partition("/")
        if not owner or not repo:
            return {"error": "نام مخزن نامعتبر"}

        ctx: Dict[str, Any] = {"repo": repo_full_name}

        # اطلاعات پایه
        info = await self._fetch_json(
            f"{GITHUB_API}/repos/{repo_full_name}", headers
        )
        if info:
            ctx["description"] = info.get("description") or ""
            ctx["language"] = info.get("language") or ""
            ctx["topics"] = info.get("topics", [])
            ctx["default_branch"] = info.get("default_branch", "main")
            branch = branch or ctx["default_branch"]

        # README
        readme = await self._fetch_json(
            f"{GITHUB_API}/repos/{repo_full_name}/readme", headers
        )
        if readme and readme.get("content"):
            try:
                ctx["readme"] = base64.b64decode(readme["content"]).decode("utf-8", errors="ignore")[
                    :8000
                ]
            except Exception:
                ctx["readme"] = ""

        # Tree (محدود)
        tree_data = await self._fetch_json(
            f"{GITHUB_API}/repos/{repo_full_name}/git/trees/{branch or 'main'}?recursive=1",
            headers,
        )
        if tree_data and isinstance(tree_data.get("tree"), list):
            files = [t["path"] for t in tree_data["tree"] if t.get("type") == "blob"]
            ctx["files_count"] = len(files)
            ctx["files_sample"] = files[:max_tree]
            ctx["truncated"] = bool(tree_data.get("truncated"))

        # Commits
        commits = await self._fetch_json(
            f"{GITHUB_API}/repos/{repo_full_name}/commits?per_page=10", headers
        )
        if isinstance(commits, list):
            ctx["recent_commits"] = [
                {
                    "sha": c.get("sha", "")[:7],
                    "message": (c.get("commit", {}).get("message") or "").split("\n")[0][:200],
                    "author": (c.get("commit", {}).get("author") or {}).get("name", ""),
                    "date": (c.get("commit", {}).get("author") or {}).get("date", ""),
                }
                for c in commits[:10]
            ]

        # Open issues
        issues = await self._fetch_json(
            f"{GITHUB_API}/repos/{repo_full_name}/issues?state=open&per_page=20", headers
        )
        if isinstance(issues, list):
            ctx["open_issues"] = [
                {
                    "number": i.get("number"),
                    "title": (i.get("title") or "")[:200],
                    "is_pr": "pull_request" in i,
                }
                for i in issues
            ]

        # Package / dependency files (برای تحلیل امنیتی/سلامت)
        package_files: Dict[str, str] = {}
        candidates = [
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
            "go.mod",
            "Cargo.toml",
            "Gemfile",
            "composer.json",
            "pom.xml",
        ]
        for fname in candidates:
            data = await self._fetch_json(
                f"{GITHUB_API}/repos/{repo_full_name}/contents/{fname}", headers
            )
            if data and data.get("type") == "file" and data.get("content"):
                try:
                    decoded = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")[:5000]
                    package_files[fname] = decoded
                except Exception:
                    pass
        if package_files:
            ctx["package_files"] = package_files

        return ctx

    # ====================================================================
    # AI helpers
    # ====================================================================

    async def _ai_generate(
        self, prompt: str, model_id: Optional[str] = None, max_tokens: int = 3000, temperature: float = 0.3
    ) -> str:
        """تولید پاسخ با AI Manager موجود (یک مدل)."""
        from .ai_manager import get_ai_manager
        from .ai_base import Message

        manager = get_ai_manager()
        models = manager.get_available_models()
        if not models:
            raise RuntimeError("هیچ مدل AI فعالی نیست. ابتدا کلید API تنظیم کنید.")

        chosen = None
        if model_id:
            for m in models:
                if m.id == model_id:
                    chosen = m
                    break
        if chosen is None:
            chosen = models[0]

        response = await manager.generate(
            model_id=chosen.id,
            messages=[Message(role="user", content=prompt)],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.content if hasattr(response, "content") else str(response)

    async def _ai_generate_multi(
        self,
        prompt: str,
        model_ids: List[str],
        max_tokens: int = 3000,
        temperature: float = 0.3,
    ) -> List[Dict[str, str]]:
        """اجرای چند مدل به‌صورت موازی و برگرداندن همه پاسخ‌ها."""
        from .ai_manager import get_ai_manager
        from .ai_base import Message

        manager = get_ai_manager()
        available = {m.id: m for m in manager.get_available_models()}
        if not available:
            raise RuntimeError("هیچ مدل AI فعالی نیست.")

        targets: List[str] = []
        for mid in model_ids or []:
            if mid in available:
                targets.append(mid)
        if not targets:
            # fallback: اولین مدل
            targets = [next(iter(available))]

        async def _run_one(mid: str) -> Dict[str, str]:
            try:
                resp = await manager.generate(
                    model_id=mid,
                    messages=[Message(role="user", content=prompt)],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = resp.content if hasattr(resp, "content") else str(resp)
                return {"model_id": mid, "content": content, "error": ""}
            except Exception as e:
                return {"model_id": mid, "content": "", "error": str(e)}

        results = await asyncio.gather(*[_run_one(m) for m in targets])
        return list(results)

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """استخراج اولین JSON معتبر از خروجی مدل."""
        if not text:
            return None
        # حذف ```json
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # تلاش با پیدا کردن { ... }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                return None
        return None

    # ====================================================================
    # Watched projects CRUD
    # ====================================================================

    async def list_watched(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self.watched]

    async def add_watched(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        repo = payload.get("repo_full_name", "").strip()
        if not repo or "/" not in repo:
            raise ValueError("repo_full_name نامعتبر")

        # بررسی تکراری
        for w in self.watched:
            if w.repo_full_name == repo:
                return w.to_dict()

        w = WatchedProject(
            id=str(uuid.uuid4()),
            repo_full_name=repo,
            repo_url=payload.get("repo_url") or f"https://github.com/{repo}",
            private=bool(payload.get("private", False)),
            default_branch=payload.get("default_branch") or "main",
            language=payload.get("language") or "",
            user_notes=payload.get("user_notes", ""),
            tags=payload.get("tags", []) or [],
            schedule_enabled=bool(payload.get("schedule_enabled", False)),
            interval_hours=float(payload.get("interval_hours", 24.0)),
            autonomy_level=payload.get("autonomy_level", "manual"),
            allow_push=bool(payload.get("allow_push", False)),
        )
        if w.schedule_enabled:
            w.next_run_at = (
                datetime.now(timezone.utc) + timedelta(hours=w.interval_hours)
            ).isoformat()
        async with self._lock:
            self.watched.append(w)
            self._save_watched()
        return w.to_dict()

    async def update_watched(self, watched_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with self._lock:
            for w in self.watched:
                if w.id == watched_id:
                    allowed = {
                        "user_notes",
                        "tags",
                        "schedule_enabled",
                        "interval_hours",
                        "autonomy_level",
                        "allow_push",
                        "allow_create_issue",
                        "scan_interval_hours",
                    }
                    for k, v in updates.items():
                        if k in allowed:
                            setattr(w, k, v)
                    w.updated_at = now_iso()
                    if w.schedule_enabled:
                        w.next_run_at = (
                            datetime.now(timezone.utc) + timedelta(hours=w.interval_hours)
                        ).isoformat()
                    else:
                        w.next_run_at = None
                    self._save_watched()
                    return w.to_dict()
        return None

    async def delete_watched(self, watched_id: str) -> bool:
        async with self._lock:
            before = len(self.watched)
            self.watched = [w for w in self.watched if w.id != watched_id]
            removed = len(self.watched) < before
            if removed:
                self._save_watched()
            return removed

    def _find_watched(self, watched_id: str) -> Optional[WatchedProject]:
        for w in self.watched:
            if w.id == watched_id:
                return w
        return None

    # ====================================================================
    # Tasks
    # ====================================================================

    async def list_tasks(
        self,
        watched_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = self.tasks
        if watched_id:
            items = [t for t in items if t.watched_id == watched_id]
        if status:
            items = [t for t in items if t.status == status]
        if priority:
            items = [t for t in items if t.priority == priority]
        return [t.to_dict() for t in items]

    async def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        watched_id = payload.get("watched_id")
        watched = self._find_watched(watched_id) if watched_id else None
        if watched_id and not watched:
            raise ValueError("پروژه تحت نظارت یافت نشد")

        title = payload.get("title", "").strip() or "تسک بدون عنوان"
        prompt = payload.get("prompt", "").strip()
        if not prompt:
            raise ValueError("prompt خالی است")

        t = OversightTask(
            id=str(uuid.uuid4()),
            watched_id=watched_id,
            project_full_name=watched.repo_full_name if watched else payload.get("project_full_name", ""),
            title=title,
            prompt=prompt,
            raw_idea=payload.get("raw_idea", ""),
            type=payload.get("type", "other"),
            priority=payload.get("priority", "medium"),
            status=payload.get("status", "pending"),
            deadline=payload.get("deadline"),
            source=payload.get("source", "user"),
        )
        async with self._lock:
            self.tasks.append(t)
            self._save_tasks()
        return t.to_dict()

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with self._lock:
            for t in self.tasks:
                if t.id == task_id:
                    allowed = {
                        "title",
                        "prompt",
                        "type",
                        "priority",
                        "status",
                        "deadline",
                        "last_summary",
                        "next_run_at",
                    }
                    for k, v in updates.items():
                        if k in allowed:
                            setattr(t, k, v)
                    t.updated_at = now_iso()
                    self._save_tasks()
                    return t.to_dict()
        return None

    async def delete_task(self, task_id: str) -> bool:
        async with self._lock:
            before = len(self.tasks)
            self.tasks = [t for t in self.tasks if t.id != task_id]
            removed = len(self.tasks) < before
            if removed:
                self._save_tasks()
            return removed

    # ====================================================================
    # Idea -> Strong Prompt
    # ====================================================================

    async def idea_to_prompt(
        self,
        idea: str,
        watched_id: Optional[str],
        type_: str = "other",
        priority: str = "medium",
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not idea.strip():
            raise ValueError("ایده خالی است")

        watched = self._find_watched(watched_id) if watched_id else None
        ctx_text = ""
        if watched:
            try:
                ctx = await self.build_project_context(watched.repo_full_name)
                summary_lines = []
                if ctx.get("description"):
                    summary_lines.append(f"توضیح ریپو: {ctx['description']}")
                if ctx.get("language"):
                    summary_lines.append(f"زبان اصلی: {ctx['language']}")
                if ctx.get("topics"):
                    summary_lines.append(f"تاپیک‌ها: {', '.join(ctx['topics'])}")
                if ctx.get("readme"):
                    summary_lines.append(f"README (خلاصه):\n{ctx['readme'][:1500]}")
                if ctx.get("files_sample"):
                    summary_lines.append(
                        f"نمونه فایل‌ها ({ctx.get('files_count', 0)} مجموع):\n"
                        + "\n".join(ctx["files_sample"][:30])
                    )
                if ctx.get("recent_commits"):
                    summary_lines.append(
                        "آخرین کامیت‌ها:\n"
                        + "\n".join(
                            f"- {c['sha']} {c['message']}" for c in ctx["recent_commits"][:8]
                        )
                    )
                if ctx.get("open_issues"):
                    summary_lines.append(
                        "issues باز:\n"
                        + "\n".join(f"- #{i['number']} {i['title']}" for i in ctx["open_issues"][:8])
                    )
                ctx_text = "\n\n".join(summary_lines)
            except Exception as e:
                logger.warning(f"context build failed: {e}")

        system_prompt = f"""تو یک معمار ارشد نرم‌افزاری. وظیفه‌ات این است که ایده/مشکل/درخواست خام کاربر را به یک پرامپت کاملاً اجرایی، دقیق و ساختار یافته تبدیل کنی.

# Context پروژه
{ctx_text or 'پروژه مشخص نیست'}

# ایده/درخواست خام کاربر
نوع: {type_}
اولویت: {priority}
متن:
\"\"\"
{idea.strip()}
\"\"\"

# خروجی موردانتظار
یک JSON دقیقاً با این ساختار برگردان (و فقط همین JSON بدون متن اضافی):

{{
  "title": "عنوان کوتاه و گویا تسک",
  "prompt": "پرامپت کامل و قدرتمند اجرایی با این ساختار:\\n## هدف\\n...\\n## Context\\n...\\n## مراحل اجرا\\n1. ...\\n2. ...\\n## معیارهای پذیرش (Acceptance Criteria)\\n- ...\\n## خروجی مورد انتظار\\n..."
}}

پرامپت باید به فارسی، طولانی، عملی، با مراحل قابل اجرا، معیار پذیرش، و خروجی مشخص باشد."""

        try:
            effective_models = model_ids or ([model_id] if model_id else None)
            if effective_models and len(effective_models) > 1:
                multi = await self._ai_generate_multi(
                    system_prompt, model_ids=effective_models, max_tokens=2500, temperature=0.4
                )
                # برای idea_to_prompt، طولانی‌ترین پاسخ معتبر را انتخاب می‌کنیم
                best = max(
                    (m for m in multi if not m.get("error") and m.get("content")),
                    key=lambda m: len(m["content"]),
                    default=None,
                )
                response = best["content"] if best else (multi[0]["content"] if multi else "")
            else:
                response = await self._ai_generate(
                    system_prompt,
                    model_id=(effective_models[0] if effective_models else None),
                    max_tokens=2500,
                    temperature=0.4,
                )
        except Exception as e:
            raise RuntimeError(f"خطا در تولید پرامپت: {e}")

        parsed = self._extract_json(response)
        if not parsed or "prompt" not in parsed:
            # fallback: کل خروجی را پرامپت بدان
            return {
                "title": (idea.strip().split("\n")[0])[:80],
                "prompt": response.strip(),
                "raw_response": response,
            }

        return {
            "title": parsed.get("title") or (idea.strip().split("\n")[0])[:80],
            "prompt": parsed.get("prompt") or response.strip(),
            "raw_response": response,
        }

    # ====================================================================
    # Run task -> evaluate via AI
    # ====================================================================

    async def run_task(
        self,
        task_id: str,
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task is None:
            raise ValueError("تسک یافت نشد")

        watched = self._find_watched(task.watched_id) if task.watched_id else None

        # ست کردن وضعیت
        async with self._lock:
            task.status = "running"
            task.runs_count += 1
            task.last_run_at = now_iso()
            task.updated_at = now_iso()
            self._save_tasks()

        try:
            ctx = {}
            ctx_text = ""
            if watched:
                try:
                    ctx = await self.build_project_context(watched.repo_full_name)
                    parts = []
                    if ctx.get("description"):
                        parts.append(f"توضیح: {ctx['description']}")
                    if ctx.get("readme"):
                        parts.append(f"README:\n{ctx['readme'][:3000]}")
                    if ctx.get("files_sample"):
                        parts.append(
                            f"فایل‌ها ({ctx.get('files_count', 0)}):\n"
                            + "\n".join(ctx["files_sample"][:40])
                        )
                    if ctx.get("recent_commits"):
                        parts.append(
                            "کامیت‌های اخیر:\n"
                            + "\n".join(
                                f"- {c['sha']} ({c['date'][:10]}) {c['message']}"
                                for c in ctx["recent_commits"]
                            )
                        )
                    if ctx.get("open_issues"):
                        parts.append(
                            "Issues باز:\n"
                            + "\n".join(
                                f"- #{i['number']} {i['title']}" for i in ctx["open_issues"]
                            )
                        )
                    ctx_text = "\n\n".join(parts)
                except Exception as e:
                    logger.warning(f"build_project_context failed: {e}")

            evaluation_prompt = f"""تو ناظر فنی و QA حرفه‌ای هستی. وظیفه‌ات بررسی این تسک در پروژه گیت‌هاب است.

# تسک
عنوان: {task.title}
نوع: {task.type}
اولویت: {task.priority}
پرامپت کامل:
\"\"\"
{task.prompt}
\"\"\"

# وضعیت فعلی پروژه
{ctx_text or 'context در دسترس نیست'}

# وظیفه تو
بر اساس تسک و وضعیت پروژه، تشخیص بده که آیا این تسک:
- کاملاً انجام شده (done)
- بخشی انجام شده (partial)
- اصلاً شروع نشده (not_done)

و گزارشی ساختار یافته بنویس.

# خروجی موردانتظار (فقط JSON)
{{
  "status": "done | partial | not_done",
  "done_parts": ["بخش‌هایی که انجام شده"],
  "remaining_parts": ["بخش‌هایی که باقی مانده"],
  "evidence": {{
    "commits": ["sha کامیت‌های مرتبط"],
    "files": ["فایل‌های مرتبط"],
    "issues": ["شماره issues مرتبط"]
  }},
  "next_actions": ["اقدامات بعدی پیشنهادی به ترتیب اولویت"],
  "confidence_score": 0.0,
  "summary": "خلاصه یک‌پاراگرافی"
}}"""

            # حالت چند-مدل (consensus)
            effective_models = model_ids or ([model_id] if model_id else None)
            if effective_models and len(effective_models) > 1:
                multi = await self._ai_generate_multi(
                    evaluation_prompt,
                    model_ids=effective_models,
                    max_tokens=3000,
                    temperature=0.2,
                )
                # consensus: انتخاب پاسخ معتبرترین (بیشترین confidence_score)
                best_parsed: Dict[str, Any] = {}
                best_score = -1.0
                best_response = ""
                best_model = ""
                all_responses: List[Dict[str, Any]] = []
                for r in multi:
                    parsed_r = self._extract_json(r["content"]) or {}
                    all_responses.append(
                        {
                            "model_id": r["model_id"],
                            "status": parsed_r.get("status"),
                            "summary": parsed_r.get("summary"),
                            "error": r.get("error", ""),
                        }
                    )
                    score = float(parsed_r.get("confidence_score") or 0.0)
                    if score > best_score and not r.get("error"):
                        best_score = score
                        best_parsed = parsed_r
                        best_response = r["content"]
                        best_model = r["model_id"]
                parsed = best_parsed
                response = best_response or (multi[0]["content"] if multi else "")
                used_model = best_model
                evidence_extra = {"consensus": all_responses}
            else:
                response = await self._ai_generate(
                    evaluation_prompt,
                    model_id=(effective_models[0] if effective_models else None),
                    max_tokens=3000,
                    temperature=0.2,
                )
                parsed = self._extract_json(response) or {}
                used_model = effective_models[0] if effective_models else ""
                evidence_extra = {}

            status_val = parsed.get("status") or "partial"
            if status_val not in ("done", "partial", "not_done", "error"):
                status_val = "partial"

            evidence = parsed.get("evidence") or {}
            if evidence_extra:
                evidence.update(evidence_extra)

            report = OversightReport(
                id=str(uuid.uuid4()),
                task_id=task.id,
                watched_id=task.watched_id,
                project_full_name=task.project_full_name,
                run_at=now_iso(),
                status=status_val,
                done_parts=parsed.get("done_parts") or [],
                remaining_parts=parsed.get("remaining_parts") or [],
                evidence=evidence,
                next_actions=parsed.get("next_actions") or [],
                confidence_score=float(parsed.get("confidence_score") or 0.0),
                raw_response=response[:8000],
                model_id=used_model,
            )

            # وضعیت نهایی
            if status_val == "done":
                final_status = "done"
            elif status_val == "not_done":
                final_status = "pending"
            else:
                final_status = "awaiting_review"

            async with self._lock:
                task.status = final_status
                task.last_summary = parsed.get("summary") or response[:300]
                for mid in (effective_models or []):
                    if mid and mid not in task.models_used:
                        task.models_used.append(mid)
                task.updated_at = now_iso()
                self.reports.insert(0, report)
                self._save_reports()
                self._save_tasks()

            # ساخت GitHub issue در حالت auto یا allow_create_issue
            if watched and final_status != "done":
                try:
                    issue_result = await self._create_github_issue_for_action(watched, task, report)
                    if issue_result and issue_result.get("success"):
                        report.evidence["github_issue"] = {
                            "number": issue_result.get("issue_number"),
                            "url": issue_result.get("issue_url"),
                        }
                        async with self._lock:
                            self._save_reports()
                except Exception as e:
                    logger.warning(f"github issue creation skipped: {e}")

            # event
            await self._emit(
                "task.completed",
                {"task": task.to_dict(), "report": report.to_dict()},
            )

            return {"task": task.to_dict(), "report": report.to_dict()}

        except Exception as e:
            logger.exception("run_task failed")
            async with self._lock:
                task.status = "failed"
                task.last_summary = f"خطا: {e}"
                task.updated_at = now_iso()
                self._save_tasks()
            raise

    # ====================================================================
    # Reports
    # ====================================================================

    async def list_reports(
        self, task_id: Optional[str] = None, watched_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        items = self.reports
        if task_id:
            items = [r for r in items if r.task_id == task_id]
        if watched_id:
            items = [r for r in items if r.watched_id == watched_id]
        return [r.to_dict() for r in items[:limit]]

    async def mark_report(
        self, report_id: str, read: Optional[bool] = None, flagged: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        async with self._lock:
            for r in self.reports:
                if r.id == report_id:
                    if read is not None:
                        r.read = read
                    if flagged is not None:
                        r.flagged = flagged
                    self._save_reports()
                    return r.to_dict()
        return None

    # ====================================================================
    # Auto scan: detect needs/issues
    # ====================================================================

    async def scan_project(self, watched_id: str, model_id: Optional[str] = None) -> Dict[str, Any]:
        watched = self._find_watched(watched_id)
        if not watched:
            raise ValueError("پروژه یافت نشد")

        ctx = await self.build_project_context(watched.repo_full_name)

        # خلاصهٔ فایل‌های package برای تحلیل dependency
        package_summary = ""
        if ctx.get("package_files"):
            parts: List[str] = []
            for fname, content in (ctx["package_files"] or {}).items():
                parts.append(f"=== {fname} ===\n{content[:1500]}")
            package_summary = "\n\n".join(parts)

        scan_prompt = f"""تو یک Senior Code Auditor و Security Engineer هستی. این پروژه را با دقت بررسی کن و یک فهرست کامل از «نیازها، ایرادات، تناقضات، آسیب‌پذیری‌ها و پیشنهادات بهبود» تهیه کن.

# پروژه
{watched.repo_full_name}
{watched.user_notes or ''}

# وضعیت
{json.dumps(
    {
        'description': ctx.get('description'),
        'language': ctx.get('language'),
        'files_count': ctx.get('files_count'),
        'files_sample': (ctx.get('files_sample') or [])[:40],
        'open_issues': (ctx.get('open_issues') or [])[:10],
        'recent_commits': (ctx.get('recent_commits') or [])[:6],
    },
    ensure_ascii=False,
    indent=2,
)}

# README (بخشی)
{(ctx.get('readme') or '')[:3000]}

# فایل‌های Dependency
{package_summary or '(فایل package یافت نشد)'}

# وظیفه
حداکثر ۸ نیاز مهم پیدا کن. حتماً بررسی کن:
- **آسیب‌پذیری‌های امنیتی** (وابستگی‌های قدیمی، secret در کد، endpointهای ناامن)
- **تناقضات کد** (anti-pattern، dead code، duplicate logic)
- **Issues باز قدیمی** که مدت‌ها لمس نشده‌اند
- **مستندات ناقص یا قدیمی** (README, CHANGELOG, نبود examples)
- **تست‌های گم‌شده یا ناکافی**
- **پیشرفت ناقص قابلیت‌ها**

هر مورد شامل:
- title (کوتاه)
- type (bug | refactor | docs | feature_request | other)
- priority (low | medium | high | critical)
- description (پاراگراف کامل)
- proposed_action (پیشنهاد عملی)

# خروجی فقط JSON
{{
  "needs": [
    {{ "title": "...", "type": "...", "priority": "...", "description": "...", "proposed_action": "..." }}
  ]
}}"""

        try:
            response = await self._ai_generate(
                scan_prompt, model_id=model_id, max_tokens=2500, temperature=0.3
            )
        except Exception as e:
            raise RuntimeError(f"خطا در scan: {e}")

        parsed = self._extract_json(response) or {}
        needs = parsed.get("needs") or []

        created_tasks: List[Dict[str, Any]] = []
        for n in needs:
            try:
                title = (n.get("title") or "").strip()[:200]
                if not title:
                    continue
                full_prompt = (
                    f"## هدف\n{title}\n\n"
                    f"## توضیح\n{n.get('description', '')}\n\n"
                    f"## اقدام پیشنهادی\n{n.get('proposed_action', '')}\n\n"
                    f"## معیارهای پذیرش\n- اعمال تغییر در پروژه\n- بدون شکست تست‌ها\n"
                    f"- مستندسازی تغییر در README یا CHANGELOG"
                )
                t = OversightTask(
                    id=str(uuid.uuid4()),
                    watched_id=watched.id,
                    project_full_name=watched.repo_full_name,
                    title=title,
                    prompt=full_prompt,
                    raw_idea=n.get("description", ""),
                    type=n.get("type", "other"),
                    priority=n.get("priority", "medium"),
                    status="suggested",
                    source="auto_scan",
                )
                async with self._lock:
                    self.tasks.append(t)
                created_tasks.append(t.to_dict())
            except Exception:
                continue

        async with self._lock:
            self._save_tasks()

        return {
            "success": True,
            "created_count": len(created_tasks),
            "tasks": created_tasks,
            "raw_response": response[:4000],
        }

    # ====================================================================
    # Tasks by project_full_name (برای صفحه پروژه‌ها)
    # ====================================================================

    async def list_tasks_by_project(self, project_full_name: str) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks if t.project_full_name == project_full_name]

    # ====================================================================
    # Settings
    # ====================================================================

    async def get_settings(self) -> Dict[str, Any]:
        return dict(self.settings)

    async def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "default_models",
            "allow_auto_push_global",
            "max_parallel_runs",
            "scan_interval_hours",
        }
        async with self._lock:
            for k, v in updates.items():
                if k in allowed:
                    self.settings[k] = v
            self._save_settings()
        return dict(self.settings)

    async def status_summary(self) -> Dict[str, Any]:
        return {
            "github_token": bool(get_github_token()),
            "render_token": bool(get_render_token()),
            "watched_count": len(self.watched),
            "tasks_count": len(self.tasks),
            "reports_count": len(self.reports),
            "tasks_by_status": {
                s: sum(1 for t in self.tasks if t.status == s)
                for s in (
                    "pending",
                    "running",
                    "awaiting_review",
                    "done",
                    "failed",
                    "cancelled",
                    "suggested",
                )
            },
            "settings": self.settings,
        }

    # ====================================================================
    # Run-now for an entire watched (همه‌ی pendingها)
    # ====================================================================

    async def run_all_pending_for_watched(
        self, watched_id: str, model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """اجرای فوری همهٔ تسک‌های pending یک پروژه."""
        watched = self._find_watched(watched_id)
        if not watched:
            raise ValueError("پروژه یافت نشد")

        pending = [t for t in self.tasks if t.watched_id == watched_id and t.status == "pending"]
        if not pending:
            return {"success": True, "ran_count": 0, "message": "تسک pending برای اجرا نیست"}

        ran: List[Dict[str, Any]] = []
        for t in pending:
            try:
                result = await self.run_task(t.id, model_id=model_id)
                ran.append({"task_id": t.id, "status": "ok", "report_id": result["report"]["id"]})
            except Exception as e:
                logger.warning(f"run_all_pending: task {t.id} failed: {e}")
                ran.append({"task_id": t.id, "status": "error", "error": str(e)})

        return {"success": True, "ran_count": len(ran), "results": ran}

    # ====================================================================
    # GitHub issue / PR creation (auto mode)
    # ====================================================================

    async def _create_github_issue_for_action(
        self, watched: WatchedProject, task: OversightTask, report: OversightReport
    ) -> Optional[Dict[str, Any]]:
        """ساخت issue روی GitHub بر اساس next_actions گزارش."""
        if not (watched.allow_create_issue or (watched.autonomy_level == "auto" and watched.allow_push)):
            return None
        if report.status == "done":
            return None
        if not report.next_actions and not report.remaining_parts:
            return None

        token = get_github_token()
        if not token:
            return None

        owner, _, repo = watched.repo_full_name.partition("/")
        if not owner or not repo:
            return None

        # عنوان و بدنه
        title = f"[oversight] {task.title[:100]}"

        body_parts: List[str] = []
        body_parts.append(f"## درخواست\n{task.raw_idea or task.title}")
        if report.remaining_parts:
            body_parts.append("## باقی‌مانده\n" + "\n".join(f"- {p}" for p in report.remaining_parts))
        if report.next_actions:
            body_parts.append("## اقدامات بعدی پیشنهادی\n" + "\n".join(f"- {a}" for a in report.next_actions))
        body_parts.append(f"\n---\n*این Issue توسط oversight (تسک `{task.id}`، اعتماد {int(report.confidence_score * 100)}%) ایجاد شده است.*")
        body = "\n\n".join(body_parts)

        labels = ["oversight", f"priority: {task.priority}", f"type: {task.type}"]

        try:
            from .github_pr_service import get_github_pr_service

            pr_service = get_github_pr_service()
            return await pr_service.create_issue(
                owner=owner, repo=repo, title=title, body=body, labels=labels, token=token
            )
        except Exception as e:
            logger.warning(f"create_github_issue failed: {e}")
            return None

    # ====================================================================
    # Event hooks (for cross-page integration)
    # ====================================================================

    _subscribers: List[Any] = []  # callbacks: (event_name: str, payload: dict) -> awaitable|None

    def subscribe(self, callback) -> None:
        """ثبت یک callback برای دریافت رویدادهای oversight."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        for cb in list(self._subscribers):
            try:
                res = cb(event, payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.warning(f"subscriber error on {event}: {e}")

    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        for r in self.reports:
            if r.id == report_id:
                return r.to_dict()
        return None

    # ====================================================================
    # Scheduler tick (با scan دوره‌ای)
    # ====================================================================

    async def scheduler_tick(self) -> Dict[str, Any]:
        """یک نوبت اجرای scheduler. تسک‌های موعد‌رسیده را اجرا می‌کند، scan دوره‌ای انجام می‌دهد."""
        now = datetime.now(timezone.utc)
        ran: List[str] = []
        scanned: List[str] = []
        max_runs = int(self.settings.get("max_parallel_runs") or 2)

        for w in list(self.watched):
            # 1) Scan دوره‌ای (حتی اگر schedule_enabled نباشد، تا scan_interval خودش جدا باشد)
            try:
                if w.scan_interval_hours and w.scan_interval_hours > 0:
                    last_scan = (
                        datetime.fromisoformat(w.last_scan_at)
                        if w.last_scan_at
                        else None
                    )
                    if last_scan is None or (now - last_scan) >= timedelta(hours=w.scan_interval_hours):
                        if w.schedule_enabled:  # فقط اگر زمان‌بندی فعال است auto-scan شود
                            try:
                                await self.scan_project(w.id, model_id=None)
                                w.last_scan_at = now.isoformat()
                                w.next_scan_at = (now + timedelta(hours=w.scan_interval_hours)).isoformat()
                                scanned.append(w.id)
                            except Exception as e:
                                logger.warning(f"auto-scan {w.id} failed: {e}")
            except Exception as e:
                logger.warning(f"scan check {w.id} failed: {e}")

            # 2) اجرای تسک‌های pending در زمان‌بندی
            if not w.schedule_enabled:
                continue
            try:
                next_dt = (
                    datetime.fromisoformat(w.next_run_at)
                    if w.next_run_at
                    else now - timedelta(seconds=1)
                )
            except Exception:
                next_dt = now - timedelta(seconds=1)
            if next_dt > now:
                continue

            pending = [t for t in self.tasks if t.watched_id == w.id and t.status == "pending"]
            if not pending:
                w.next_run_at = (now + timedelta(hours=w.interval_hours)).isoformat()
                w.last_run_at = now.isoformat()
                continue

            for t in pending[:max_runs]:
                try:
                    await self.run_task(t.id, model_id=None)
                    ran.append(t.id)
                except Exception as e:
                    logger.warning(f"scheduled run_task {t.id} failed: {e}")

            w.last_run_at = now.isoformat()
            w.next_run_at = (now + timedelta(hours=w.interval_hours)).isoformat()

        async with self._lock:
            self._save_watched()

        return {
            "ran": ran,
            "ran_count": len(ran),
            "scanned": scanned,
            "scanned_count": len(scanned),
            "tick_at": now.isoformat(),
        }


# ====================================================================
# Singleton
# ====================================================================

_service: Optional[OversightService] = None


def get_oversight_service() -> OversightService:
    global _service
    if _service is None:
        _service = OversightService()
    return _service


# ====================================================================
# Background loop (called from main.py lifespan)
# ====================================================================

async def oversight_scheduler_loop(stop_event: asyncio.Event, interval_seconds: int = 60) -> None:
    service = get_oversight_service()
    logger.info("Oversight scheduler loop started")
    while not stop_event.is_set():
        try:
            await service.scheduler_tick()
        except Exception as e:
            logger.exception(f"oversight tick failed: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
    logger.info("Oversight scheduler loop stopped")
