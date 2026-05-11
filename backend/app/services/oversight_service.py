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
# مسیرها (lazy initialization — هرگز در زمان import crash نمی‌کند)
# ====================================================================

def _resolve_storage_dir() -> Path:
    """تعیین مسیر قابل نوشتن برای ذخیره. اگر مسیر اصلی قابل دسترس نبود، fallback به /tmp."""
    candidates = [
        os.environ.get("OVERSIGHT_STORAGE", "").strip(),
        "./storage/oversight",
        "/tmp/oversight",
    ]
    for c in candidates:
        if not c:
            continue
        try:
            p = Path(c)
            p.mkdir(parents=True, exist_ok=True)
            # تست نوشتنی بودن
            test = p / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return p
        except Exception as e:
            logger.warning(f"oversight storage path '{c}' not writable: {e}")
            continue
    # آخرین fallback: in-memory only (هیچ‌چیز ذخیره نمی‌شود)
    logger.warning("oversight: no writable storage path - using ephemeral in-memory only")
    return Path("/tmp")  # برای جلوگیری از None اما write_json در try/except است


STORAGE_DIR = _resolve_storage_dir()

WATCHED_FILE = STORAGE_DIR / "watched_projects.json"
TASKS_FILE = STORAGE_DIR / "tasks.json"
REPORTS_FILE = STORAGE_DIR / "reports.json"
SETTINGS_FILE = STORAGE_DIR / "settings.json"
REPOS_CACHE_FILE = STORAGE_DIR / "repos_cache.json"

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
    # 🆕 تنظیمات autonomy گسترش‌یافته
    default_execution_mode: str = "manual"  # manual | auto_via_projects_page | auto_via_pr
    verify_only_mode: bool = False
    confirmation_streak_required: int = 2
    max_apply_retries: int = 2
    auto_create_pr_instead_of_commit: bool = True
    notify_user_before_apply: bool = False
    last_verify_at: Optional[str] = None
    next_verify_at: Optional[str] = None
    verify_interval_hours: float = 12.0
    # 🆕 وزن‌های قابل تنظیم برای محاسبهٔ per-file health score
    # (مهاجرت از Health analysis criteria_weights)
    # default values متعادل — کاربر می‌تواند override کند تا محاسبه
    # به اولویت‌های پروژهٔ خودش حساس‌تر شود
    scan_criteria_weights: Dict[str, float] = field(default_factory=lambda: {
        "security": 1.5,
        "quality": 1.0,
        "tests": 1.2,
        "completeness": 1.0,
        # 🆕 (P3) وزن‌های جدید برای passهای logic + functional
        "logical_alignment": 1.0,
        "functional_correctness": 1.5,
    })
    # 🆕 عمق scan قابل تنظیم (مهاجرت از Health depth parameter)
    # quick: 3 pass، standard: 5 pass، deep: همه ۱۰ pass،
    # thorough: همه ۱۰ + per-file scoring + roadmap auto-gen
    scan_depth: str = "deep"  # quick | standard | deep | thorough
    # 🆕 (P1) مدل‌های انتخابی برای auto-scan از scheduler — مستقل از frontend
    # session. اگر خالی باشد، scheduler از default backend استفاده می‌کند.
    # اگر بیش از ۱ مدل، رفتار consensus اعمال می‌شود (هر pass با همهٔ مدل‌ها
    # و ادغام findings).
    selected_models: List[str] = field(default_factory=list)
    # 🆕 (P4) خلاصهٔ آخرین scan — برای نمایش در UI WatchedCard accordion
    # ست در پایان run_deep_scan. شامل: model_used, depth, passes_run,
    # files_analyzed_count, findings_count, tasks_created, duplicates_skipped,
    # critical_count, scan_id, completed_at, pass_breakdown
    last_scan_metadata: Optional[Dict[str, Any]] = None
    # 🆕 (Creator) منبع auto-add: 'creator_via_web' | 'creator_via_telegram' |
    # 'github_import' | 'manual_api' | None
    # برای نمایش badge در UI WatchedCard و audit trail
    auto_added_source: Optional[str] = None
    # 🆕 (auto-loop) ping-pong scheduler-driven:
    # اگر فعال، پس از verify=partial scheduler خودکار:
    #   1. status تسک به pending برمی‌گردد
    #   2. apply‌ٔ مجدد با followup_prompt
    #   3. verify خودکار
    # تا verify=done شود یا max_auto_loop_rounds برسد یا regress رخ دهد
    # فقط وقتی autonomy_level=auto و execution_mode auto_via_* معنی دارد
    auto_continue_until_done: bool = False
    max_auto_loop_rounds: int = 5
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
    # 🆕 جداسازی execution از verification
    execution_mode: str = "manual"  # manual | auto_via_projects_page | auto_via_pr
    verification_status: str = "pending"
    # pending | applied_externally_pending_verify | partial | done | regressed | needs_clarification
    verification_history: List[Dict[str, Any]] = field(default_factory=list)
    applied_evidence: Dict[str, Any] = field(default_factory=dict)
    manually_marked_applied_at: Optional[str] = None
    last_verified_at: Optional[str] = None
    confirmation_streak: int = 0
    last_verification_report_id: Optional[str] = None
    apply_retries: int = 0
    # location hints (extracted from prompt for faster verify)
    target_files: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    # 🆕 followup prompt — وقتی verify نتیجهٔ partial/not_done/regressed/error
    # داد، AI یک پرامپت ادامه (focused on remaining_parts) تولید می‌کند که
    # کاربر می‌تواند کپی یا با دکمهٔ "اجرای بعدی با AI" اعمال کند.
    # وقتی verify='done' شد، این فیلدها reset می‌شوند.
    followup_prompt: str = ""
    followup_generated_at: Optional[str] = None
    followup_target_locations: List[Dict[str, Any]] = field(default_factory=list)
    followup_acceptance_criteria: List[str] = field(default_factory=list)
    followup_round: int = 0  # 0=هیچ، 1=دور اول follow-up، 2=...
    # 🆕 findings که در این task ادغام شده‌اند (از smart merger در deep_scan)
    # هر merged finding شامل: title, type, priority, _pass, description (snippet)
    merged_findings: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    # 🆕 (P3) archive flag — تسک‌های done که از فهرست اصلی پنهان شده‌اند
    # backward-compat: اگر در JSON نباشد، False خوانده می‌شود
    archived: bool = False
    archived_at: Optional[str] = None
    # 🆕 (P1) metadata scan که این task را تولید کرده — برای شفافیت در UI
    # هر تسک نمایش می‌دهد: مدل، depth، passes، files_count، scan_id
    # برای task‌های قدیمی (قبل از این تغییر): None
    created_by_scan_metadata: Optional[Dict[str, Any]] = None
    # 🆕 (P2) cross-scan tracking — چندبار این task در scan‌های متوالی دیده شد
    scan_seen_count: int = 1
    last_seen_in_scan_at: Optional[str] = None
    # 🆕 (P4) prompt history — وقتی پرامپت regenerate می‌شود، نسخهٔ قبلی اینجا
    # ذخیره می‌شود (max 10 آیتم). هر آیتم: {prompt, raw_idea, model_id, generated_at}
    prompt_history: List[Dict[str, Any]] = field(default_factory=list)

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
    # 🆕 معیار راهنما + Codex
    user_goal: str = ""
    touched_codex: Dict[str, Any] = field(default_factory=dict)

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
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        tmp.replace(path)
    except Exception as e:
        # نباید هرگز کل اپ را به خاطر یک نوشتن disk به مشکل بیندازد
        logger.warning(f"oversight: failed to write {path}: {e}")


# ====================================================================
# Service
# ====================================================================

class OversightService:
    """سرویس اصلی نظارت."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._session: Optional[aiohttp.ClientSession] = None
        self._subscribers: List[Any] = []

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

        try:
            self._load_all()
        except Exception as e:
            logger.warning(f"oversight: load failed (continuing with empty state): {e}")

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

    def _read_repos_cache(self) -> Optional[Dict[str, Any]]:
        """خواندن کش لیست مخازن از دیسک."""
        try:
            data = _read_json(REPOS_CACHE_FILE, None)
            if data and isinstance(data, dict) and isinstance(data.get("repos"), list):
                return data
        except Exception as e:
            logger.debug(f"repos cache read failed: {e}")
        return None

    async def list_user_repos(
        self, max_pages: int = 5, force_refresh: bool = False, max_cache_age_seconds: int = 21600
    ) -> Dict[str, Any]:
        """دریافت repos کاربر (شامل private). با cache روی دیسک تا 6 ساعت."""
        # سرو از cache در حالت غیر-force
        if not force_refresh:
            cached = self._read_repos_cache()
            if cached:
                synced_at_str = cached.get("synced_at")
                fresh = False
                if synced_at_str:
                    try:
                        synced_dt = datetime.fromisoformat(synced_at_str)
                        age = (datetime.now(timezone.utc) - synced_dt).total_seconds()
                        fresh = age <= max_cache_age_seconds
                    except Exception:
                        pass
                if fresh:
                    return {
                        "success": True,
                        "repos": cached["repos"],
                        "count": len(cached["repos"]),
                        "synced_at": synced_at_str,
                        "from_cache": True,
                    }

        token = get_github_token()
        if not token:
            # حتی بدون توکن، اگر کش داریم همان را برگردان
            cached = self._read_repos_cache()
            if cached:
                return {
                    "success": True,
                    "repos": cached.get("repos", []),
                    "count": len(cached.get("repos", [])),
                    "synced_at": cached.get("synced_at"),
                    "from_cache": True,
                    "warning": "توکن گیت‌هاب تنظیم نشده — از کش قبلی استفاده شد",
                }
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
            # در صورت timeout، اگر cache داریم همان را برگردان
            cached = self._read_repos_cache()
            if cached:
                return {
                    "success": True,
                    "repos": cached.get("repos", []),
                    "count": len(cached.get("repos", [])),
                    "synced_at": cached.get("synced_at"),
                    "from_cache": True,
                    "warning": "Timeout در ارتباط با GitHub — از کش قبلی استفاده شد",
                }
            return {"success": False, "error": "Timeout در ارتباط با GitHub", "repos": all_repos}
        except aiohttp.ClientError as e:
            cached = self._read_repos_cache()
            if cached:
                return {
                    "success": True,
                    "repos": cached.get("repos", []),
                    "count": len(cached.get("repos", [])),
                    "synced_at": cached.get("synced_at"),
                    "from_cache": True,
                    "warning": f"خطای شبکه — از کش قبلی استفاده شد ({e})",
                }
            return {"success": False, "error": f"خطای شبکه: {str(e)}", "repos": all_repos}

        # ذخیرهٔ cache
        synced_at = now_iso()
        try:
            _write_json(
                REPOS_CACHE_FILE,
                {"repos": all_repos, "synced_at": synced_at, "count": len(all_repos)},
            )
        except Exception as e:
            logger.debug(f"repos cache write failed: {e}")

        return {
            "success": True,
            "repos": all_repos,
            "count": len(all_repos),
            "synced_at": synced_at,
            "from_cache": False,
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

        # 🆕 (Creator) defaults هوشمندانه: اگر کاربر صریحاً override نکرده،
        # autonomy=auto و schedule فعال و execution=manual (apply با کلیک)
        w = WatchedProject(
            id=str(uuid.uuid4()),
            repo_full_name=repo,
            repo_url=payload.get("repo_url") or f"https://github.com/{repo}",
            private=bool(payload.get("private", False)),
            default_branch=payload.get("default_branch") or "main",
            language=payload.get("language") or "",
            user_notes=payload.get("user_notes", ""),
            tags=payload.get("tags", []) or [],
            schedule_enabled=bool(payload.get("schedule_enabled", True)),
            interval_hours=float(payload.get("interval_hours", 24.0)),
            autonomy_level=payload.get("autonomy_level", "auto"),
            allow_push=bool(payload.get("allow_push", False)),
            default_execution_mode=payload.get("default_execution_mode", "manual"),
            verify_only_mode=bool(payload.get("verify_only_mode", False)),
            scan_interval_hours=float(payload.get("scan_interval_hours", 168.0)),
            scan_depth=payload.get("scan_depth", "deep"),
            auto_continue_until_done=bool(payload.get("auto_continue_until_done", False)),
            auto_added_source=payload.get("auto_added_source"),
        )
        if w.schedule_enabled:
            w.next_run_at = (
                datetime.now(timezone.utc) + timedelta(hours=w.interval_hours)
            ).isoformat()
        async with self._lock:
            self.watched.append(w)
            self._save_watched()
        return w.to_dict()

    async def auto_register_watched(
        self,
        repo_full_name: str,
        *,
        source: str = "unknown",
        user_notes: str = "",
        repo_url: str = "",
        default_branch: str = "main",
        language: str = "",
        private: bool = False,
    ) -> Dict[str, Any]:
        """🆕 خودکار یک پروژهٔ GitHub را به watched اضافه می‌کند با defaults هوشمند.

        پیش‌فرض‌ها:
        - schedule_enabled = True
        - autonomy_level = "auto" (scan خودکار)
        - default_execution_mode = "manual" (apply با کلیک)
        - verify_only_mode = False
        - auto_continue_until_done = False (loop خاموش)
        - scan_depth = "deep"
        - scan_interval_hours = 168 (هفتگی)
        - interval_hours = 24

        اگر قبلاً موجود است:
        - duplicate نمی‌سازد
        - فقط source را در user_notes append می‌کند (به‌عنوان audit trail)
        """
        repo = (repo_full_name or "").strip()
        if not repo or "/" not in repo:
            raise ValueError("repo_full_name نامعتبر")

        # duplicate check
        for w in self.watched:
            if w.repo_full_name == repo:
                # append source به user_notes (audit trail)
                if source and source not in (w.user_notes or ""):
                    audit_note = f"\n[auto-re-registered from {source} at {now_iso()}]"
                    async with self._lock:
                        w.user_notes = (w.user_notes or "") + audit_note
                        w.updated_at = now_iso()
                        self._save_watched()
                return {**w.to_dict(), "_was_duplicate": True}

        # ساخت WatchedProject با defaults هوشمند
        new_notes = user_notes or f"[auto-added from {source}]"
        w = WatchedProject(
            id=str(uuid.uuid4()),
            repo_full_name=repo,
            repo_url=repo_url or f"https://github.com/{repo}",
            private=private,
            default_branch=default_branch or "main",
            language=language or "",
            user_notes=new_notes,
            tags=[],
            schedule_enabled=True,
            interval_hours=24.0,
            autonomy_level="auto",
            allow_push=False,
            default_execution_mode="manual",
            verify_only_mode=False,
            scan_interval_hours=168.0,
            scan_depth="deep",
            auto_continue_until_done=False,
            auto_added_source=source,
        )
        # next_run_at — فوراً اولین scan در یک ساعت آینده برنامه‌ریزی شود
        now = datetime.now(timezone.utc)
        w.next_run_at = (now + timedelta(hours=1)).isoformat()
        w.next_scan_at = (now + timedelta(hours=1)).isoformat()

        async with self._lock:
            self.watched.append(w)
            self._save_watched()
        result = w.to_dict()
        result["_was_duplicate"] = False

        # notification (silent skip اگر env vars نباشد)
        try:
            from .notification_service import notification_service
            await notification_service.notify_event(
                "project_auto_watched",
                f"👁 *پروژه خودکار تحت نظارت قرار گرفت*\n"
                f"📁 `{repo}`\n"
                f"🔗 source: `{source}`\n"
                f"✓ autonomy: auto (scan خودکار)\n"
                f"✓ execution: manual (apply با کلیک)\n"
                f"✓ scan_depth: deep · بازه: 168h",
                subject="Auto-watched",
                priority="low",
                project_name=repo,
                watched_id=w.id,
            )
        except Exception as _e:
            logger.debug(f"auto_register_watched notification skipped: {_e}")

        return result

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
                        "default_execution_mode",
                        "verify_only_mode",
                        "confirmation_streak_required",
                        "max_apply_retries",
                        "auto_create_pr_instead_of_commit",
                        "notify_user_before_apply",
                        "verify_interval_hours",
                        # 🆕 (commit 2.3) — مهاجرت از Health analysis settings
                        "scan_depth",
                        "scan_criteria_weights",
                        # 🆕 (auto-loop) ping-pong scheduler-driven
                        "auto_continue_until_done",
                        "max_auto_loop_rounds",
                        # 🆕 (P1) مدل‌های auto-scan
                        "selected_models",
                        # 🆕 (Creator) منبع auto-add
                        "auto_added_source",
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
        from .oversight_strong_prompt import extract_target_files, extract_acceptance_criteria

        watched_id = payload.get("watched_id")
        watched = self._find_watched(watched_id) if watched_id else None
        if watched_id and not watched:
            raise ValueError("پروژه تحت نظارت یافت نشد")

        title = payload.get("title", "").strip() or "تسک بدون عنوان"
        prompt = payload.get("prompt", "").strip()
        if not prompt:
            raise ValueError("prompt خالی است")

        # استخراج target_files و acceptance_criteria از پرامپت در صورت نبودن
        target_files = payload.get("target_files") or extract_target_files(prompt)
        acceptance_criteria = (
            payload.get("acceptance_criteria") or extract_acceptance_criteria(prompt)
        )

        execution_mode = payload.get("execution_mode")
        if not execution_mode:
            execution_mode = (watched.default_execution_mode if watched else "manual") or "manual"

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
            execution_mode=execution_mode,
            target_files=target_files,
            acceptance_criteria=acceptance_criteria,
        )
        async with self._lock:
            self.tasks.append(t)
            self._save_tasks()
        return t.to_dict()

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from .oversight_strong_prompt import extract_target_files, extract_acceptance_criteria

        async with self._lock:
            for t in self.tasks:
                if t.id == task_id:
                    allowed = {
                        "title",
                        "prompt",
                        "raw_idea",  # 🆕 (P4) برای regenerate prompt
                        "type",
                        "priority",
                        "status",
                        "deadline",
                        "last_summary",
                        "next_run_at",
                        "execution_mode",
                        "target_files",
                        "acceptance_criteria",
                        "verification_status",
                        "archived",  # 🆕 (P3)
                    }
                    for k, v in updates.items():
                        if k in allowed:
                            setattr(t, k, v)
                            # وقتی archived true شد، archived_at را ست کن
                            if k == "archived" and v:
                                t.archived_at = now_iso()
                            elif k == "archived" and not v:
                                t.archived_at = None
                    # اگر prompt تغییر کرده، target_files و AC را هم به‌روز کن
                    if "prompt" in updates and updates["prompt"]:
                        if not updates.get("target_files"):
                            t.target_files = extract_target_files(t.prompt)
                        if not updates.get("acceptance_criteria"):
                            t.acceptance_criteria = extract_acceptance_criteria(t.prompt)
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

    # 🆕 (P4) regenerate prompt با حفظ history — راه ارتقای پرامپت‌های قدیمی
    async def regenerate_prompt_for_task(
        self,
        task_id: str,
        *,
        new_raw_idea: Optional[str] = None,
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """پرامپت تسک را با raw_idea (جدید یا فعلی) بازتولید می‌کند.
        نسخهٔ قبلی به prompt_history منتقل می‌شود (max 10 آیتم).
        تسک جدیدی ساخته نمی‌شود — همان task به‌روز می‌شود.
        """
        # 1) پیدا کردن task
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return None

        # 2) raw_idea مورد استفاده
        raw = (new_raw_idea or "").strip() or (task.raw_idea or "").strip() or task.title
        if not raw:
            raise ValueError("راه‌اندازی regenerate نیاز به raw_idea یا title دارد")

        # 3) نسخهٔ فعلی را در history ذخیره کن (قبل از replace)
        history_entry = {
            "prompt": task.prompt,
            "raw_idea": task.raw_idea or "",
            "model_id": (task.models_used[0] if task.models_used else "") or "",
            "generated_at": task.updated_at or task.created_at,
        }

        # 4) idea_to_prompt را صدا بزن
        try:
            new_data = await self.idea_to_prompt(
                idea=raw,
                watched_id=task.watched_id,
                type_=task.type,
                priority=task.priority,
                model_id=model_id,
                model_ids=model_ids,
            )
        except Exception as e:
            # transaction-safe: اگر AI fail شد، چیزی تغییر نمی‌کند
            raise RuntimeError(f"بازتولید پرامپت ناموفق: {e}")

        # 5) فقط حالا history را push کن و تسک را به‌روز کن (atomic)
        async with self._lock:
            # دوباره پیدا کن چون async lock
            task = next((t for t in self.tasks if t.id == task_id), None)
            if not task:
                return None
            task.prompt_history.insert(0, history_entry)
            task.prompt_history = task.prompt_history[:10]  # cap به 10
            task.raw_idea = raw
            task.prompt = new_data.get("prompt") or task.prompt
            new_target_files = new_data.get("target_files") or []
            new_ac = new_data.get("acceptance_criteria") or []
            if new_target_files:
                task.target_files = new_target_files
            if new_ac:
                task.acceptance_criteria = new_ac
            if model_id:
                task.models_used = [model_id]
            task.updated_at = now_iso()
            self._save_tasks()
            return task.to_dict()

    # ====================================================================
    # 🆕 (Daily Report) محاسبه‌های گزارش دوره‌ای
    # ====================================================================

    async def compute_project_health_report(self, watched_id: str) -> Dict[str, Any]:
        """گزارش سلامت کامل یک پروژه — برای استفاده در daily/global report.

        خروجی شامل:
        - health_score, security_score, completeness_score, standard_score (0-100)
        - tasks breakdown (total, active, done, pending, by priority)
        - top_critical_findings (تا ۳ تای اول)
        - last_scan metadata
        - attention_priority (0-100) و attention_label
        """
        from datetime import datetime, timezone, timedelta
        watched = self._find_watched(watched_id)
        if not watched:
            return {
                "watched_id": watched_id,
                "project_full_name": "",
                "error": "watched not found",
            }

        repo_name = watched.repo_full_name

        # tasks مربوط به این watched
        all_tasks = [t for t in self.tasks if t.watched_id == watched_id]
        active_tasks = [
            t for t in all_tasks
            if t.status not in ("done", "cancelled")
            and not getattr(t, "archived", False)
            and t.verification_status not in ("done",)
        ]
        done_tasks = [t for t in all_tasks if t.verification_status == "done" or t.status == "done"]
        pending_tasks = [t for t in active_tasks if t.status == "pending"]

        # breakdown by priority (active tasks)
        priority_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for t in active_tasks:
            p = (t.priority or "medium").lower()
            if p in priority_breakdown:
                priority_breakdown[p] += 1

        # top_critical_findings — تا ۳ تای اول
        critical_active = sorted(
            [t for t in active_tasks if (t.priority or "").lower() == "critical"],
            key=lambda t: -(getattr(t, "scan_seen_count", 1) or 1),
        )[:3]
        top_critical_findings = [
            {
                "title": (t.title or "")[:120],
                "task_id": t.id,
                "scan_seen_count": getattr(t, "scan_seen_count", 1) or 1,
            }
            for t in critical_active
        ]

        # scan metadata
        last_scan_meta = getattr(watched, "last_scan_metadata", None) or {}
        last_scan_at = last_scan_meta.get("completed_at") or watched.last_scan_at
        last_scan_depth = last_scan_meta.get("scan_depth") or getattr(watched, "scan_depth", "deep")
        scan_seen_top_count = max(
            (getattr(t, "scan_seen_count", 1) or 1 for t in active_tasks),
            default=1,
        )

        # ===== امتیازها =====
        # health_score: ابتدا از last_scan_metadata، وگرنه از فرمول task-based
        SEVERITY_PENALTY = {"critical": 25, "high": 12, "medium": 5, "low": 2}
        if last_scan_meta.get("findings_count") is not None and last_scan_meta.get("critical_count") is not None:
            # اگر scan داده‌ها داده، ترکیب: 100 - penalty * task_severity_sum
            penalty = sum(
                SEVERITY_PENALTY.get((t.priority or "medium").lower(), 5)
                for t in active_tasks
            )
            health_score = max(0.0, min(100.0, 100.0 - penalty * 0.5))
        else:
            penalty = sum(
                SEVERITY_PENALTY.get((t.priority or "medium").lower(), 5)
                for t in active_tasks
            )
            health_score = max(0.0, min(100.0, 100.0 - penalty * 0.5))

        # security_score: متمرکز روی tasks با _pass=security/security_deep
        security_active = []
        for t in active_tasks:
            meta = getattr(t, "created_by_scan_metadata", None) or {}
            ppass = meta.get("_pass", "")
            if ppass in ("security", "security_deep"):
                security_active.append(t)
        if security_active:
            sec_penalty = sum(
                SEVERITY_PENALTY.get((t.priority or "medium").lower(), 5)
                for t in security_active
            )
            security_score = max(0.0, min(100.0, 100.0 - sec_penalty))
        else:
            security_score = 95.0  # هیچ مشکل امنیتی شناسایی‌شده — خوش‌بین

        # completeness_score
        total_for_completeness = len(all_tasks)
        if total_for_completeness > 0:
            completeness_score = (len(done_tasks) / total_for_completeness) * 100.0
        else:
            completeness_score = 0.0

        # standard_score: میانگین weighted health با criteria_weights
        weights = getattr(watched, "scan_criteria_weights", None) or {
            "security": 1.5, "quality": 1.0, "tests": 1.2, "completeness": 1.0,
            "logical_alignment": 1.0, "functional_correctness": 1.5,
        }
        # ساده: weighted average از health/security/completeness
        w_sec = float(weights.get("security", 1.5))
        w_qual = float(weights.get("quality", 1.0))
        w_comp = float(weights.get("completeness", 1.0))
        total_w = w_sec + w_qual + w_comp
        standard_score = (
            (security_score * w_sec) + (health_score * w_qual) + (completeness_score * w_comp)
        ) / max(total_w, 0.001)

        # attention_priority
        avg_seen = (
            sum(getattr(t, "scan_seen_count", 1) or 1 for t in active_tasks) / len(active_tasks)
            if active_tasks else 0
        )
        # age_factor: اگر آخرین scan قدیمی است، attention بالاتر
        age_factor = 0.0
        if last_scan_at:
            try:
                last_dt = datetime.fromisoformat(last_scan_at.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - last_dt).total_seconds() / 86400
                age_factor = min(20.0, age_days * 1.0)
            except Exception:
                age_factor = 0.0

        attention_priority = min(100.0, (
            priority_breakdown["critical"] * 30
            + priority_breakdown["high"] * 15
            + (avg_seen - 1) * 10
            + age_factor
        ))
        if attention_priority >= 80:
            attention_label = "CRITICAL"
        elif attention_priority >= 60:
            attention_label = "HIGH"
        elif attention_priority >= 40:
            attention_label = "MEDIUM"
        else:
            attention_label = "LOW"

        return {
            "watched_id": watched_id,
            "project_full_name": repo_name,
            "health_score": round(health_score, 1),
            "security_score": round(security_score, 1),
            "completeness_score": round(completeness_score, 1),
            "standard_score": round(standard_score, 1),
            "tasks_total": len(all_tasks),
            "tasks_active": len(active_tasks),
            "tasks_done": len(done_tasks),
            "tasks_pending": len(pending_tasks),
            "tasks_priority_breakdown": priority_breakdown,
            "top_critical_findings": top_critical_findings,
            "last_scan_at": last_scan_at,
            "last_scan_depth": last_scan_depth,
            "scan_seen_top_count": scan_seen_top_count,
            "attention_priority": round(attention_priority, 1),
            "attention_label": attention_label,
        }

    async def compute_global_health_summary(self) -> Dict[str, Any]:
        """خلاصهٔ کلی همهٔ پروژه‌های watched — برای daily report."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        cutoff_30d = now - timedelta(days=30)

        # محاسبه per-project
        projects: List[Dict[str, Any]] = []
        for w in self.watched:
            try:
                rep = await self.compute_project_health_report(w.id)
                if rep.get("error"):
                    continue
                projects.append(rep)
            except Exception as e:
                logger.warning(f"compute_project_health_report failed for {w.id}: {e}")

        # sort by attention_priority desc
        projects.sort(key=lambda p: -p.get("attention_priority", 0))

        # global aggregates
        watched_count = len(projects)
        total_active = sum(p.get("tasks_active", 0) for p in projects)
        total_critical = sum(
            p.get("tasks_priority_breakdown", {}).get("critical", 0) for p in projects
        )
        total_high = sum(
            p.get("tasks_priority_breakdown", {}).get("high", 0) for p in projects
        )

        # تعداد تسک‌های done در ۳۰ روز اخیر
        total_done_last_30d = 0
        for t in self.tasks:
            if t.status != "done" and t.verification_status != "done":
                continue
            updated = t.updated_at or t.created_at
            try:
                u_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if u_dt.tzinfo is None:
                    u_dt = u_dt.replace(tzinfo=timezone.utc)
                if u_dt >= cutoff_30d:
                    total_done_last_30d += 1
            except Exception:
                continue

        global_health_avg = (
            sum(p.get("health_score", 0) for p in projects) / max(watched_count, 1)
        ) if watched_count else 0.0
        global_security_avg = (
            sum(p.get("security_score", 0) for p in projects) / max(watched_count, 1)
        ) if watched_count else 0.0

        # top_findings_global — top 5 critical/high from all projects
        all_findings: List[Dict[str, Any]] = []
        for p in projects:
            for cf in p.get("top_critical_findings", []):
                all_findings.append({
                    "project_full_name": p["project_full_name"],
                    "title": cf["title"],
                    "priority": "critical",
                    "task_id": cf["task_id"],
                    "scan_seen_count": cf["scan_seen_count"],
                })
        # add high priority active tasks too
        for w in self.watched:
            high_tasks = sorted(
                [
                    t for t in self.tasks
                    if t.watched_id == w.id
                    and (t.priority or "").lower() == "high"
                    and t.status not in ("done", "cancelled")
                    and not getattr(t, "archived", False)
                    and t.verification_status not in ("done",)
                ],
                key=lambda t: -(getattr(t, "scan_seen_count", 1) or 1),
            )[:2]
            for t in high_tasks:
                all_findings.append({
                    "project_full_name": w.repo_full_name,
                    "title": (t.title or "")[:120],
                    "priority": "high",
                    "task_id": t.id,
                    "scan_seen_count": getattr(t, "scan_seen_count", 1) or 1,
                })
        # sort: critical first، سپس scan_seen_count desc
        all_findings.sort(
            key=lambda f: (
                0 if f["priority"] == "critical" else 1,
                -f.get("scan_seen_count", 1),
            )
        )
        top_findings_global = all_findings[:5]

        # توصیه‌های دینامیک
        recommendations: List[str] = []
        if total_critical > 0:
            top_crit_proj = next(
                (p for p in projects if p.get("tasks_priority_breakdown", {}).get("critical", 0) > 0),
                None,
            )
            if top_crit_proj:
                recommendations.append(
                    f"ابتدا {top_crit_proj['tasks_priority_breakdown']['critical']} مورد critical در "
                    f"`{top_crit_proj['project_full_name']}` را بررسی کنید"
                )
        # high streak
        high_streak_count = sum(
            1 for t in self.tasks
            if (getattr(t, "scan_seen_count", 1) or 1) > 2
            and t.status not in ("done", "cancelled")
            and not getattr(t, "archived", False)
        )
        if high_streak_count > 0:
            recommendations.append(
                f"{high_streak_count} تسک با scan_seen >2 دارید — این‌ها در چندین scan متوالی شناسایی شده ولی هنوز انجام نشده‌اند"
            )
        # پروژه‌های CRITICAL attention
        crit_projects = [p for p in projects if p.get("attention_label") == "CRITICAL"]
        if crit_projects:
            names = ", ".join(f"`{p['project_full_name']}`" for p in crit_projects[:3])
            recommendations.append(f"پروژه‌های با attention=CRITICAL: {names}")
        if not recommendations:
            recommendations.append("✅ همهٔ پروژه‌ها در وضعیت پایدار — هیچ اقدام فوری لازم نیست")

        # 🆕 (Creator) آمار پروژه‌های ساخته‌شده و auto-watched در ۳۰ روز اخیر
        projects_created_30d = 0
        projects_auto_watched_30d = 0
        recent_created: List[Dict[str, Any]] = []
        for w in self.watched:
            try:
                if not w.auto_added_source:
                    continue
                # بررسی created_at در ۳۰ روز اخیر
                created_iso = w.created_at
                try:
                    c_dt = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if c_dt < cutoff_30d:
                    continue
                projects_auto_watched_30d += 1
                if w.auto_added_source in ("creator_via_web", "creator_via_telegram"):
                    projects_created_30d += 1
                recent_created.append({
                    "name": w.repo_full_name,
                    "created_at": w.created_at,
                    "source": w.auto_added_source,
                    "watched_id": w.id,
                })
            except Exception:
                continue
        # sort by created_at desc
        recent_created.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        recent_created = recent_created[:5]

        return {
            "generated_at": now.isoformat(),
            "watched_count": watched_count,
            "total_active_tasks": total_active,
            "total_critical": total_critical,
            "total_high": total_high,
            "total_done_last_30d": total_done_last_30d,
            "global_health_avg": round(global_health_avg, 1),
            "global_security_avg": round(global_security_avg, 1),
            "projects": projects,
            "top_findings_global": top_findings_global,
            "recommendations": recommendations,
            # 🆕 (Creator) آمار creator
            "projects_created_last_30d": projects_created_30d,
            "projects_auto_watched_last_30d": projects_auto_watched_30d,
            "recent_created_projects": recent_created,
        }

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
        user_goal = ""
        deep_ctx: Dict[str, Any] = {}  # خروجی build_deep_context_for_idea (محتوای واقعی)
        if watched:
            user_goal = (watched.user_notes or "").strip()
            # ✨ Deep context: محتوای ۱۸ فایل برتر با شمارهٔ خط + نقشهٔ
            # importهای داخلی + special filesها (README، tsconfig، ...)
            # بدون این مرحله، AI فقط نام فایل‌ها را می‌بیند و پرامپتش
            # عمومی و جدا از پروژه می‌شود.
            try:
                token_for_deep = get_github_token()
                if token_for_deep:
                    from .oversight_deep_scan_service import build_deep_context_for_idea
                    # 🆕 (P2) max_deep_read از 18 به 30 افزایش یافت — context
                    # پربارتر برای پرامپت تولیدشده (شامل manifests + tests + config)
                    deep_ctx = await build_deep_context_for_idea(
                        watched.repo_full_name,
                        branch=watched.default_branch or "main",
                        token=token_for_deep,
                        max_deep_read=40,  # 🆕 از 30 به 40 — context پربارتر برای پرامپت دقیق‌تر
                    )
                    if not deep_ctx.get("ok"):
                        logger.warning(f"deep_context for idea failed: {deep_ctx.get('error')}")
                        deep_ctx = {}
            except Exception as _e:
                logger.warning(f"build_deep_context_for_idea exception: {_e}")
                deep_ctx = {}

            # Context سطحی: README + commits + issues — همچنان مفید است
            try:
                ctx = await self.build_project_context(watched.repo_full_name)
                summary_lines = []
                if ctx.get("description"):
                    summary_lines.append(f"توضیح ریپو: {ctx['description']}")
                if ctx.get("language"):
                    summary_lines.append(f"زبان اصلی: {ctx['language']}")
                if ctx.get("topics"):
                    summary_lines.append(f"تاپیک‌ها: {', '.join(ctx['topics'])}")
                if deep_ctx.get("ok") and deep_ctx.get("stacks"):
                    summary_lines.append(f"Stack تشخیص داده شده: {', '.join(deep_ctx['stacks'])}")
                if ctx.get("readme"):
                    summary_lines.append(f"README (خلاصه):\n{ctx['readme'][:1500]}")
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

        # ─── ساخت system prompt متناسب با موجود بودن یا نبودن deep_ctx ───
        deep_block = ""
        deep_rules_block = ""
        if deep_ctx.get("ok"):
            files_summary = deep_ctx.get("files_summary", "")
            deep_blob = deep_ctx.get("deep_files_blob", "")
            pkg_blob = deep_ctx.get("package_files_blob", "")
            spec_blob = deep_ctx.get("special_files_blob", "")
            graph_blob = deep_ctx.get("import_graph_summary", "")
            deep_paths = deep_ctx.get("deep_paths", [])
            deep_block = f"""
# 📂 ساختار کامل پروژه ({deep_ctx.get('files_count', 0)} فایل — نمونه)
{files_summary}

# 📄 محتوای فایل‌های کلیدی (با شمارهٔ خط — به این‌ها استناد کن)
{deep_blob[:60000]}

# 📦 فایل‌های Dependency
{pkg_blob[:8000] if pkg_blob else '(فایل dependency پیدا نشد)'}

# 📚 فایل‌های context ویژه (README، tsconfig، next.config، docs)
{spec_blob[:12000] if spec_blob else '(context ویژه‌ای موجود نیست)'}

# 🌐 نقشهٔ Importهای داخلی (هاب‌های پروژه)
{graph_blob if graph_blob else '(گراف import محاسبه نشد)'}
"""
            deep_rules_block = f"""
# 🚨 قانون استناد (الزامی برای جلوگیری از پرامپت‌های توخالی)
- **هر `target_locations[i].path` که می‌نویسی، باید واقعاً در «ساختار کامل پروژه» بالا موجود باشد** — حق ساختن مسیر فرضی نداری.
- **`lines`** را از روی شمارهٔ خط‌های واقعی در «محتوای فایل‌های کلیدی» انتخاب کن. اگر خط دقیقی پیدا نکردی، lines را خالی بگذار (نه عدد ساختگی).
- **`snippet`** باید **عیناً همان متنی** باشد که در «محتوای فایل‌های کلیدی» با شمارهٔ خط مشخص آمده. اگر در deep blob موجود نیست، snippet را خالی بگذار.
- **`related_files`** را از «نقشهٔ Importهای داخلی» استخراج کن (فایل‌هایی که path هدف را import می‌کنند یا بالعکس). نه حدس عمومی.
- **`dependency_summary`** را با ذکر نام واقعی فایل‌ها/توابع از پروژه بنویس — نه جملات قالبی.
- **`tech_context`**: Stack تشخیص داده شده در بالا = `{', '.join(deep_ctx.get('stacks', [])) or '(نامشخص)'}` — از همین استفاده کن.
- **`risks`**: ریسک‌های واقعی این کدبیس را بگو (مثلاً «این تابع از ۳ روتر import می‌شود؛ تغییرش روی همه اثر دارد») — نه جملات کلی مثل «احتیاط در استقرار کنید».
- **`validation_commands`**: بر اساس Stack واقعی پیشنهاد بده (pytest برای پایتون، npm run test برای JS).

اگر هیچ‌کدام از فایل‌های deep-read با ایدهٔ کاربر مرتبط نبود، **به‌صراحت** بنویس:
  در `note` بگذار: "این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند"
  ولی `path` باز هم باید از «ساختار کامل پروژه» انتخاب شود (نه ساخته‌شده).

⛔ ممنوعیت‌ها:
- ❌ هرگز path اختراعی ننویس (مثل `src/utils/auth.ts` در حالی که هیچ فایلی به این نام موجود نیست).
- ❌ هرگز snippet جعلی ننویس — اگر کد دقیق نداری، خالی بگذار.
- ❌ هرگز risks عمومی ننویس — یا با نام فایل/تابع ground بده، یا کوتاه بگذار.
- ❌ هرگز فقط ایدهٔ کاربر را با کلمات حرفه‌ای‌تر بازنویسی نکن — این کار را خود کاربر می‌کرد.

✅ فایل‌های deep-read شده که می‌توانی آزادانه به آن‌ها استناد کنی:
{chr(10).join(f'  • {p}' for p in deep_paths[:25]) if deep_paths else '  (هیچ‌کدام)'}
"""

        system_prompt = f"""تو یک معمار ارشد نرم‌افزاری هستی که به repository واقعی پروژه دسترسی داری. وظیفه‌ات این است که ایده/مشکل/درخواست خام کاربر را به یک تسک ساختاریافتهٔ **مبتنی بر کد واقعی پروژه** تبدیل کنی — نه یک پرامپت عمومی.

خروجی این تسک به یک ابزار کدنویس خارجی (Cursor/Copilot/ChatGPT) داده می‌شود — پس فیلدها باید **کاملاً مشخص، grounded در کد واقعی، و قابل اعمال** باشند.

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

# 📋 Context کلی پروژه
{ctx_text or 'پروژه مشخص نیست'}
{deep_block}

# 💬 ایده/درخواست خام کاربر
نوع: {type_}
اولویت: {priority}
متن:
\"\"\"
{idea.strip()}
\"\"\"

# 📤 خروجی فقط JSON خالص (بدون متن اضافی، بدون ```)

{{
  "title": "عنوان کوتاه و گویا تسک — یک جمله قابل سنجش (فارسی)",
  "description": "پاراگراف کامل: چه چیزی، چرا، شواهد در کد واقعی پروژه (نام فایل و خط ذکر کن)",
  "proposed_action": "پیشنهاد عملی برای پیاده‌سازی — با ذکر فایل‌ها/توابع واقعی",
  "type": "bug | feature_request | refactor | docs | security | other",
  "priority": "low | medium | high | critical",
  "estimated_complexity": "small | medium | large",

  "target_locations": [
    {{
      "path": "backend/app/services/foo.py",
      "lines": "245-289",
      "symbol": "function_or_class_name",
      "snippet": "snippet دقیق از کد فعلی (همان که در deep blob دیدی)",
      "note": "این چه چیزی است / چرا اینجا"
    }}
  ],

  "related_files": [
    {{"path": "frontend/src/...", "reason": "این endpoint/کامپوننت را call می‌کند", "at_line": 78}}
  ],

  "dependency_summary": "این بخش در نقشهٔ پروژه چه نقشی دارد، با ذکر نام فایل‌های caller/importer",

  "tech_context": "Stack شناسایی‌شده + کتابخانه‌های مرتبط",

  "before_after_examples": [
    {{"label": "...", "before": "کد فعلی از deep blob", "after": "کد پیشنهادی"}}
  ],

  "acceptance_criteria": [
    "معیار قابل تست ۱ — با مرجع به فایل/تابع واقعی",
    "معیار قابل تست ۲"
  ],

  "validation_commands": ["pytest backend/...", "npm run test -- ..."],

  "risks": "ریسک‌های specific این کدبیس (نه جملات عمومی) — مثلاً 'این تابع توسط ۳ روتر استفاده می‌شود، تغییرش روی همه اثر دارد'"
}}
{deep_rules_block}

# قوانین کلی نهایی
1. path همیشه از ریشهٔ ریپو (مثل `backend/app/...` یا `frontend/src/...`).
2. acceptance_criteria باید قابل تست باشد، نه تعریف کلی.
3. عنوان و توضیحات فارسی و حرفه‌ای.
4. حداقل ۱ مورد در target_locations الزامی است (مگر اینکه ایدهٔ کاربر کاملاً غیرفنی باشد — مثلاً «اضافه کردن صفحه درباره ما»).
5. اگر deep context موجود نیست، در `note` هر location بنویس "بر اساس ساختار سطحی — توسط مجری تأیید شود".

# ⚠️ قواعد کیفیت (بسیار مهم — رعایت کن)
6. **عمق تحلیل**: قبل از پاسخ، حداقل ۱۰ فایل deep context را که در ادامه آمده **به‌طور کامل** بخوان. به نام فایل اعتماد نکن — کد را بخوان.
7. **وابستگی‌ها**: برای هر تغییری که پیشنهاد می‌دهی، در `dependency_summary` بنویس کدام فایل‌ها/توابع/state‌های دیگر تحت تأثیر قرار می‌گیرند. حداقل ۳ مورد.
8. **مدت زمان مناسب**: پاسخ سریع (زیر ۳۰ ثانیه) = پاسخ سطحی. برای پروژهٔ واقعی، حدود ۱-۳ دقیقه فکر کن. اگر هر دو deep_context و related_files خوانده‌شده، باید پاسخ غنی باشد.
9. **JSON کامل**: مطمئن شو خروجی JSON معتبر و کامل است (با `}}` نهایی). اگر فضای کمی داری، خلاصه‌تر بنویس ولی **هیچ بخش را قطع نکن**.
10. **target_locations**: حداقل ۲-۳ مورد با `snippet` کد واقعی (۳-۸ خط) از فایل‌های deep context. snippet باید چسبیده به مشکل/تغییر باشد، نه random.
11. **related_files**: حداقل ۳ فایل دیگر که تحت تأثیر قرار می‌گیرند، با `reason` مشخص.
12. **before_after_examples**: حداقل ۱ مثال قبل/بعد با کد واقعی (نه placeholder).
"""

        try:
            # 🆕 max_tokens از 4000 به 10000 افزایش — تجربه نشان داد
            # idea_to_prompt با grounded JSON ساختاریافته (شامل description،
            # related_files با snippet، acceptance_criteria، endpoints، …)
            # گاهی > 6000 token می‌شود. اگر max_tokens کم باشد:
            #   - AI زود stop می‌کند (زیر 30 ثانیه — کیفیت ضعیف)
            #   - JSON ناقص → پرامپت ناقص
            # temperature پایین برای grounding بیشتر در کد واقعی.
            effective_models = model_ids or ([model_id] if model_id else None)
            grounded_max_tokens = 10000 if deep_ctx.get("ok") else 6000
            grounded_temperature = 0.15 if deep_ctx.get("ok") else 0.3
            if effective_models and len(effective_models) > 1:
                multi = await self._ai_generate_multi(
                    system_prompt,
                    model_ids=effective_models,
                    max_tokens=grounded_max_tokens,
                    temperature=grounded_temperature,
                )
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
                    max_tokens=grounded_max_tokens,
                    temperature=grounded_temperature,
                )

            # 🆕 detection truncation: اگر response با } یا ] تمام نشد، JSON ناقص است
            def _looks_truncated(resp: str) -> bool:
                if not resp or len(resp) < 100:
                    return False
                stripped = resp.rstrip().rstrip(" `\n")
                if not stripped.endswith(("}", "]")):
                    return True
                try:
                    opens = stripped.count("{")
                    closes = stripped.count("}")
                    if opens != closes:
                        return True
                except Exception:
                    pass
                return False

            if _looks_truncated(response):
                logger.warning("idea_to_prompt response به نظر truncated است — retry با max_tokens بیشتر")
                try:
                    retry_max = min(16000, grounded_max_tokens + 4000)
                    if effective_models and len(effective_models) > 1:
                        multi = await self._ai_generate_multi(
                            system_prompt + "\n\n# ⚠️ پاسخ قبلی truncated بود — این بار خلاصه‌تر و مطمئن شو JSON کامل بسته شود.",
                            model_ids=effective_models,
                            max_tokens=retry_max,
                            temperature=grounded_temperature,
                        )
                        best = max(
                            (m for m in multi if not m.get("error") and m.get("content")),
                            key=lambda m: len(m["content"]),
                            default=None,
                        )
                        response = best["content"] if best else response
                    else:
                        response = await self._ai_generate(
                            system_prompt + "\n\n# ⚠️ پاسخ قبلی truncated بود — این بار خلاصه‌تر و مطمئن شو JSON کامل بسته شود.",
                            model_id=(effective_models[0] if effective_models else None),
                            max_tokens=retry_max,
                            temperature=grounded_temperature,
                        )
                except Exception as _retry_e:
                    logger.warning(f"idea_to_prompt retry failed: {_retry_e}")
        except Exception as e:
            raise RuntimeError(f"خطا در تولید پرامپت: {e}")

        from .oversight_strong_prompt import build_strong_prompt

        parsed = self._extract_json(response)
        if not parsed:
            # fallback: کل خروجی را پرامپت بدان
            return {
                "title": (idea.strip().split("\n")[0])[:80],
                "prompt": response.strip(),
                "target_files": [],
                "target_locations": [],
                "related_files": [],
                "acceptance_criteria": [],
                "type": type_,
                "priority": priority,
                "estimate": "medium",
                "raw_response": response,
            }

        # locations جدید + fallback به target_files قدیمی
        target_locations = parsed.get("target_locations") or []
        target_files: List[str] = list(parsed.get("target_files") or [])
        if target_locations and not target_files:
            target_files = [
                l.get("path") for l in target_locations
                if isinstance(l, dict) and l.get("path")
            ]
        if not target_locations and target_files:
            target_locations = [{"path": p} for p in target_files]

        related = parsed.get("related_files") or []
        examples = parsed.get("before_after_examples") or []
        vcmds = parsed.get("validation_commands") or []
        ac = parsed.get("acceptance_criteria") or []
        title = (parsed.get("title") or (idea.strip().split("\n")[0])[:80]).strip()

        # اگر AI خودش فیلد prompt آماده داد، احترام می‌گذاریم؛ ولی بهتر است always
        # از build_strong_prompt استفاده کنیم تا قالب یکدست بماند.
        full_prompt = build_strong_prompt(
            title=title,
            user_goal=user_goal,
            description=parsed.get("description", ""),
            proposed_action=parsed.get("proposed_action", ""),
            target_files=target_files,
            target_locations=target_locations,
            related_files=related if isinstance(related, list) else [],
            dependency_summary=(parsed.get("dependency_summary") or "").strip(),
            tech_context=(parsed.get("tech_context") or "").strip(),
            before_after_examples=examples if isinstance(examples, list) else [],
            validation_commands=vcmds if isinstance(vcmds, list) else [],
            acceptance_criteria=ac,
            risks=(parsed.get("risks") or "").strip(),
            type_=parsed.get("type") or type_,
            priority=parsed.get("priority") or priority,
            estimate=(parsed.get("estimated_complexity") or parsed.get("estimate") or "medium"),
        )
        # 🆕 safety check: اگر به هر دلیلی DISCLAIMER در ابتدا نبود، prepend کن
        from .oversight_strong_prompt import EXECUTOR_DISCLAIMER
        if "یادداشت مهم برای مدل اجراکننده" not in full_prompt[:500]:
            logger.warning("idea_to_prompt: DISCLAIMER در full_prompt نبود — prepend می‌شود")
            full_prompt = EXECUTOR_DISCLAIMER + "\n" + full_prompt

        return {
            "title": title,
            "prompt": full_prompt,
            "target_files": target_files,
            "target_locations": target_locations,
            "related_files": related,
            "acceptance_criteria": ac,
            "type": parsed.get("type") or type_,
            "priority": parsed.get("priority") or priority,
            "estimate": parsed.get("estimated_complexity") or parsed.get("estimate") or "medium",
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
            user_goal = (watched.user_notes or "").strip() if watched else ""
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

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

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

            # شناسایی فایل‌های لمس‌شده برای ضمیمه کردن Codex
            touched_paths: List[str] = list(task.target_files or [])
            try:
                from .oversight_strong_prompt import extract_target_files as _extract_tf

                if not touched_paths and task.prompt:
                    touched_paths = _extract_tf(task.prompt)
            except Exception:
                pass

            touched_codex: Dict[str, Any] = {}
            if watched and touched_paths:
                try:
                    from .oversight_codex_service import get_codex_for_files

                    touched_codex = get_codex_for_files(watched.id, touched_paths) or {}
                except Exception:
                    touched_codex = {}

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
                user_goal=(watched.user_notes if watched else "") or "",
                touched_codex=touched_codex,
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

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{(watched.user_notes or '(کاربر یادداشتی ثبت نکرده است)').strip()}

# پروژه
{watched.repo_full_name}

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

برای هر مورد، این فیلدها را با حداکثر دقت پر کن — خروجی این تسک به ابزار کدنویس خارجی (Cursor/Copilot) داده می‌شود، پس باید کاملاً قابل اعمال باشد:

- title (کوتاه و قابل سنجش)
- type (bug | refactor | docs | feature_request | security | other)
- priority (low | medium | high | critical)
- description (پاراگراف کامل: شواهد + تأثیر)
- proposed_action (پیشنهاد عملی برای رفع)
- target_locations: لیست {{path, lines, symbol, snippet, note}} — مسیر کامل از ریشهٔ ریپو، خط/بازهٔ خط، نام تابع/کلاس، و snippet کوتاه از کد فعلی
- related_files: لیست {{path, reason, at_line}} — فایل‌هایی که با این تسک مرتبط هستند (caller، importer، shared state)
- dependency_summary: نقش این بخش در پروژه و چه چیزی روی آن اثر می‌گذارد
- tech_context: پشتهٔ مرتبط (مثل "FastAPI + JWT + Next.js 14")
- before_after_examples: لیست {{label, before, after}} برای روشن کردن تغییر مورد انتظار (اختیاری ولی مفید)
- validation_commands: دستورات shell که برای تأیید رفع مشکل باید اجرا شوند
- acceptance_criteria: ۲ تا ۴ معیار قابل تست
- estimated_complexity: small | medium | large
- risks: هشدارها و رگرشن‌های احتمالی

# خروجی فقط JSON خالص (بدون متن اضافی، بدون ```)
{{
  "needs": [
    {{
      "title": "...",
      "type": "...",
      "priority": "...",
      "description": "...",
      "proposed_action": "...",
      "target_locations": [{{"path": "backend/app/...", "lines": "245-289", "symbol": "func_name", "snippet": "...", "note": "..."}}],
      "related_files": [{{"path": "...", "reason": "...", "at_line": 67}}],
      "dependency_summary": "...",
      "tech_context": "...",
      "before_after_examples": [{{"label": "...", "before": "...", "after": "..."}}],
      "validation_commands": ["pytest ...", "npm run ..."],
      "acceptance_criteria": ["...", "..."],
      "estimated_complexity": "medium",
      "risks": "..."
    }}
  ]
}}

قوانین:
1. path همیشه از ریشهٔ ریپو (مثل `backend/app/services/foo.py`).
2. اگر شمارهٔ خط دقیق نمی‌دانی، lines را خالی بگذار — ولی path الزامی است.
3. snippet حتماً مسئلهٔ مورد نظر را نشان دهد.
4. حداکثر ۸ نیاز مهم. کیفیت > کمیت.
"""

        try:
            response = await self._ai_generate(
                scan_prompt, model_id=model_id, max_tokens=2500, temperature=0.3
            )
        except Exception as e:
            raise RuntimeError(f"خطا در scan: {e}")

        parsed = self._extract_json(response) or {}
        needs = parsed.get("needs") or []

        from .oversight_strong_prompt import build_strong_prompt

        created_tasks: List[Dict[str, Any]] = []
        for n in needs:
            try:
                title = (n.get("title") or "").strip()[:200]
                if not title:
                    continue

                # locations جدید + fallback به target_files قدیمی
                target_locations = n.get("target_locations") or []
                target_files: List[str] = list(n.get("target_files") or [])
                if target_locations and not target_files:
                    target_files = [
                        l.get("path") for l in target_locations
                        if isinstance(l, dict) and l.get("path")
                    ]
                if not target_locations and target_files:
                    target_locations = [{"path": p} for p in target_files]

                related = n.get("related_files") or []
                examples = n.get("before_after_examples") or []
                vcmds = n.get("validation_commands") or []

                ac = n.get("acceptance_criteria") or []
                if not ac:
                    ac = [
                        "اعمال تغییر بدون شکستن تست‌های موجود",
                        "linter بدون warning عبور می‌کند",
                        "type-check موفق است",
                    ]

                full_prompt = build_strong_prompt(
                    title=title,
                    user_goal=watched.user_notes,
                    description=n.get("description", ""),
                    proposed_action=n.get("proposed_action", ""),
                    target_files=target_files,
                    target_locations=target_locations,
                    related_files=related if isinstance(related, list) else [],
                    dependency_summary=(n.get("dependency_summary") or "").strip(),
                    tech_context=(n.get("tech_context") or "").strip(),
                    before_after_examples=examples if isinstance(examples, list) else [],
                    validation_commands=vcmds if isinstance(vcmds, list) else [],
                    acceptance_criteria=ac,
                    risks=(n.get("risks") or "").strip(),
                    type_=n.get("type", "other"),
                    priority=n.get("priority", "medium"),
                    estimate=(n.get("estimated_complexity") or "medium"),
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
                    target_files=target_files,
                    acceptance_criteria=ac,
                    execution_mode=watched.default_execution_mode or "manual",
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
    # 🔗 External project tasks bridge — wiring /projects ↔ /oversight
    # ====================================================================
    # هدف: dynamic_fields از پروژه‌های local که action_type='github_commit'
    # دارند را به‌عنوان «تسک قابل verify» در /oversight نمایش دهیم — بدون
    # duplicate کردن داده. این تابع فقط READ است؛ هیچ فیلدی را تغییر نمی‌دهد.

    def list_external_project_tasks(
        self,
        db_session,
        project_id_filter: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[Dict[str, Any]]:
        """خواندن dynamic_fields از تمام پروژه‌های local و تبدیل آنها به ساختار
        تسک‌مانند برای نمایش در مرکز نظارت.

        فیلدهایی که شرط دارند:
          - action_type ∈ {'github_commit', 'github_multi_commit', 'file_edit'}
          - archived = false (مگر include_archived=True)

        خروجی شکل تسک Oversight را تقلید می‌کند با فیلدهای اضافی:
          - source = 'project_field'
          - origin_project_id, origin_project_name, origin_field_id
          - external_prompt (اگر روی فیلد ذخیره شده — از Commit 7)
        """
        try:
            from ..models.project import Project as _Project
        except Exception:
            return []
        out: List[Dict[str, Any]] = []
        try:
            q = db_session.query(_Project)
            if project_id_filter:
                q = q.filter(_Project.id == project_id_filter)
            for proj in q.all():
                raw = proj.dynamic_fields
                if not raw:
                    continue
                try:
                    fields = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    continue
                if not isinstance(fields, list):
                    continue
                for f in fields:
                    if not isinstance(f, dict):
                        continue
                    action_type = f.get("action_type", "display")
                    if action_type not in ("github_commit", "github_multi_commit", "file_edit"):
                        continue
                    if not include_archived and f.get("archived"):
                        continue
                    # map priority int → string
                    p_int = int(f.get("priority", 5)) if str(f.get("priority", 5)).isdigit() else 5
                    priority_str = (
                        "critical" if p_int == 1
                        else ("high" if p_int <= 3
                              else ("medium" if p_int <= 6 else "low"))
                    )
                    type_map = {
                        "github_commit": "bug",
                        "github_multi_commit": "refactor",
                        "file_edit": "refactor",
                    }
                    # last_run derived from trigger.last_executed if exists
                    trig = f.get("trigger") if isinstance(f.get("trigger"), dict) else {}
                    out.append({
                        "id": f"projfield_{proj.id}_{f.get('id', '')}",
                        "source": "project_field",
                        "origin_project_id": proj.id,
                        "origin_project_name": proj.name,
                        "origin_field_id": f.get("id", ""),
                        "watched_id": None,  # not tied to a watched repo
                        "project_full_name": proj.github_path or proj.name,
                        "title": f.get("name", "بدون عنوان")[:200],
                        "type": type_map.get(action_type, "other"),
                        "priority": priority_str,
                        "status": "archived" if f.get("archived") else "pending",
                        "prompt": f.get("external_prompt") or f.get("value", "")[:4000],
                        "raw_idea": f.get("value", "")[:1000],
                        "target_files": [f["target_path"]] if f.get("target_path") else [],
                        "target_locations": f.get("target_locations") or (
                            [{"path": f["target_path"]}] if f.get("target_path") else []
                        ),
                        "external_prompt": f.get("external_prompt", ""),
                        "execution_mode": "manual",
                        "verification_status": "pending",
                        "confirmation_streak": 0,
                        "last_run_at": trig.get("last_executed"),
                        "next_run_at": trig.get("next_run"),
                        "created_at": f.get("created_at", ""),
                        "field_type": f.get("field_type", "temporary"),
                        "action_type": action_type,
                    })
        except Exception as _e:
            logger.warning(f"list_external_project_tasks failed: {_e}")
        return out

    async def verify_external_project_field(
        self,
        db_session,
        project_id: str,
        field_id: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """verify یک dynamic_field از /projects با همان موتور verifier.

        برای این کار یک OversightTask transient (بدون ذخیره در tasks لیست)
        می‌سازیم که verifier بتواند روی آن کار کند، سپس فقط report را
        برمی‌گردانیم (تسک به storage اضافه نمی‌شود).
        """
        from ..models.project import Project as _Project
        from .oversight_strong_prompt import (
            extract_target_files as _extract_files,
            extract_acceptance_criteria as _extract_ac,
        )

        proj = db_session.query(_Project).filter(_Project.id == project_id).first()
        if not proj:
            raise ValueError("پروژه یافت نشد")

        raw = proj.dynamic_fields
        fields = []
        if raw:
            try:
                fields = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                fields = []
        target_field = None
        for f in (fields or []):
            if isinstance(f, dict) and f.get("id") == field_id:
                target_field = f
                break
        if not target_field:
            raise ValueError("فیلد یافت نشد")

        repo_full_name = proj.github_path or ""
        if "/" not in repo_full_name:
            # try to derive from github_url
            gh_url = getattr(proj, "github_url", "") or ""
            if "github.com/" in gh_url:
                repo_full_name = gh_url.split("github.com/")[-1].rstrip("/").replace(".git", "")

        prompt_text = target_field.get("external_prompt") or target_field.get("value", "")
        target_files = list(target_field.get("target_locations") and [
            l.get("path") for l in target_field["target_locations"] if isinstance(l, dict) and l.get("path")
        ] or [])
        if not target_files and target_field.get("target_path"):
            target_files = [target_field["target_path"]]
        if not target_files and prompt_text:
            target_files = _extract_files(prompt_text)

        acceptance_criteria = _extract_ac(prompt_text) if prompt_text else []
        if not acceptance_criteria:
            acceptance_criteria = ["نتیجهٔ این فیلد با مفاد آن مطابقت کند"]

        # ساخت transient task — هرگز ذخیره نمی‌شود
        task = OversightTask(
            id=f"transient_projfield_{project_id}_{field_id}",
            watched_id=None,
            project_full_name=repo_full_name,
            title=target_field.get("name", "field")[:200],
            prompt=prompt_text,
            raw_idea=target_field.get("value", "")[:1000],
            type="bug",
            priority="medium",
            status="pending",
            source="project_field_bridge",
            target_files=target_files,
            acceptance_criteria=acceptance_criteria,
            execution_mode="manual",
        )
        # موقتاً به لیست اضافه می‌کنیم تا verifier پیدا کند، بعد حذف می‌کنیم
        async with self._lock:
            self.tasks.append(task)
        try:
            from .oversight_verifier import verify_task as _verify
            result = await _verify(task.id, model_id=model_id, triggered_by="project_field_bridge")
        finally:
            async with self._lock:
                self.tasks = [t for t in self.tasks if t.id != task.id]
        return result

    # ====================================================================
    # 🚀 Inspector apply-action bridge — اتصال OversightTask به مسیر اجرای
    #    واقعی روی پروژهٔ محلی (smart-chat → apply-action → PR)
    # ====================================================================

    def resolve_project_for_task(
        self, db_session, task_id: str
    ) -> Dict[str, Any]:
        """نگاشت OversightTask → Project محلی (DB).

        استراتژی:
          الف) اگر task.watched_id موجود است، watched.repo_full_name را
               بگیر (مثل "owner/repo")
          ب) در DB دنبال Project بگرد که github_path == repo_full_name
               یا github_url حاوی این string است یا
               extra_data.owner+repo match شود
          ج) اگر پیدا نشد، matched=False با reason

        خروجی:
            {
              matched: bool,
              project_id: str,
              project_name: str,
              repo_full_name: str,
              reason: str,
            }
        """
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task is None:
            return {
                "matched": False,
                "project_id": "",
                "project_name": "",
                "repo_full_name": "",
                "reason": "تسک یافت نشد",
            }

        repo_full_name = ""
        watched = self._find_watched(task.watched_id) if task.watched_id else None
        if watched and watched.repo_full_name:
            repo_full_name = watched.repo_full_name
        elif task.project_full_name and "/" in task.project_full_name:
            repo_full_name = task.project_full_name

        if not repo_full_name or "/" not in repo_full_name:
            return {
                "matched": False,
                "project_id": "",
                "project_name": "",
                "repo_full_name": repo_full_name,
                "reason": "این تسک به یک repo GitHub معتبر (owner/repo) متصل نیست",
            }

        try:
            from ..models.project import Project as _Project
        except Exception as e:
            return {
                "matched": False,
                "project_id": "",
                "project_name": "",
                "repo_full_name": repo_full_name,
                "reason": f"بارگذاری مدل Project ناموفق: {e}",
            }

        # 1) match مستقیم روی github_path
        try:
            proj = (
                db_session.query(_Project)
                .filter(_Project.github_path == repo_full_name)
                .first()
            )
            if proj:
                return {
                    "matched": True,
                    "project_id": proj.id,
                    "project_name": proj.name,
                    "repo_full_name": repo_full_name,
                    "reason": "",
                }
        except Exception as _e:
            logger.warning(f"resolve_project: github_path query failed: {_e}")

        # 2) match روی github_url (substring)
        try:
            proj = (
                db_session.query(_Project)
                .filter(_Project.github_url.like(f"%{repo_full_name}%"))
                .first()
            )
            if proj:
                return {
                    "matched": True,
                    "project_id": proj.id,
                    "project_name": proj.name,
                    "repo_full_name": repo_full_name,
                    "reason": "",
                }
        except Exception as _e:
            logger.warning(f"resolve_project: github_url query failed: {_e}")

        # 3) match روی extra_data.owner + extra_data.repo
        try:
            owner, repo = repo_full_name.split("/", 1)
            for p in db_session.query(_Project).all():
                if not p.extra_data:
                    continue
                try:
                    ed = json.loads(p.extra_data) if isinstance(p.extra_data, str) else p.extra_data
                except Exception:
                    continue
                if isinstance(ed, dict) and ed.get("owner") == owner and ed.get("repo") == repo:
                    return {
                        "matched": True,
                        "project_id": p.id,
                        "project_name": p.name,
                        "repo_full_name": repo_full_name,
                        "reason": "",
                    }
        except Exception as _e:
            logger.warning(f"resolve_project: extra_data scan failed: {_e}")

        return {
            "matched": False,
            "project_id": "",
            "project_name": "",
            "repo_full_name": repo_full_name,
            "reason": (
                f"پروژه‌ای با repo='{repo_full_name}' در DB محلی پیدا نشد. "
                "این repo را ابتدا در صفحهٔ /projects (GitHub Import) اضافه کنید."
            ),
        }

    async def record_task_execution(
        self,
        task_id: str,
        *,
        pr_url: str,
        pr_branch: str = "",
        files_committed: Optional[List[str]] = None,
        model_ids: Optional[List[str]] = None,
        action_plan_summary: str = "",
        executed_via: str = "inspector_apply_action",
    ) -> Optional[Dict[str, Any]]:
        """ثبت اجرای موفق یک تسک از طریق Inspector apply-action.

        تغییرات روی task (همگی additive — کلیدهای موجود حفظ می‌شوند):
          - applied_evidence به‌روز می‌شود (pr_url, pr_branch, files_committed,
            model_ids, executed_via, executed_at, action_plan_summary)
          - manually_marked_applied_at = اکنون
          - verification_status = applied_externally_pending_verify
          - status = awaiting_review (اگر pending/suggested بود — وگرنه
            دست‌نخورده؛ مثلاً done نباید reset شود)
          - verification_history += یک entry نوع 'executed'

        دلیل additive: اگر کاربر این تسک را قبلاً به‌صورت دستی هم اعمال
        کرده، نباید آن evidence را پاک کنیم — هر دو ثبت می‌شوند.
        """
        files_committed = files_committed or []
        model_ids = model_ids or []

        async with self._lock:
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task is None:
                return None

            now = now_iso()
            # merge additive
            ev = dict(task.applied_evidence or {})
            ev["pr_url"] = pr_url
            if pr_branch:
                ev["pr_branch"] = pr_branch
            if files_committed:
                ev["files_committed"] = files_committed
            if model_ids:
                ev["model_ids"] = model_ids
            ev["executed_via"] = executed_via
            ev["executed_at"] = now
            if action_plan_summary:
                ev["action_plan_summary"] = action_plan_summary[:1000]
            task.applied_evidence = ev

            task.manually_marked_applied_at = now
            task.verification_status = "applied_externally_pending_verify"
            if task.status in ("pending", "suggested"):
                task.status = "awaiting_review"
            task.updated_at = now

            history = list(task.verification_history or [])
            history.append({
                "ts": now,
                "status": "executed",
                "triggered_by": executed_via,
                "summary": (action_plan_summary or f"اجرا با {executed_via}")[:500],
                "pr_url": pr_url,
                "pr_branch": pr_branch,
                "files_committed_count": len(files_committed),
            })
            task.verification_history = history[-50:]

            self._save_tasks()
            return task.to_dict()

    # ====================================================================
    # 🔁 Follow-up prompt generation — وقتی verify نتیجهٔ partial/not_done
    # داد، یک پرامپت قوی جدید focused on remaining_parts تولید می‌کنیم
    # که در دور بعدی به AI داده شود
    # ====================================================================

    async def generate_followup_prompt_for_task(
        self,
        task: "OversightTask",
        report: "OversightReport",
        watched: Optional["WatchedProject"] = None,
    ) -> Optional[str]:
        """تولید پرامپت قوی برای دور بعدی، focused on AC های ناموفق.

        شرایط:
          - فقط برای status ∈ {partial, not_done, regressed, error}
          - اگر done است → None برمی‌گرداند
          - title جدید: "ادامه (دور N): <عنوان قبلی>"
          - description: لیست done_parts + remaining_parts + summary
            verifier + لینک PR قبلی (اگر آرشیو شده در applied_evidence)
          - acceptance_criteria: فقط remaining_parts (اگر خالی،
            از next_actions استفاده می‌کند)
          - target_locations: همان قبلی + پاث‌های جدید از evidence.files
          - related_files: همان قبلی (از task.prompt استخراج)
          - validation_commands: همان قبلی (از task.prompt استخراج)
          - risks: next_actions به‌عنوان hint
          - tech_context: از watched.user_notes یا task.prompt
        """
        if report.status == "done":
            return None

        from .oversight_strong_prompt import (
            build_strong_prompt,
            extract_target_files,
            extract_target_locations,
            extract_acceptance_criteria,
        )

        # شمارهٔ دور بعدی
        next_round = (task.followup_round or 0) + 1

        # عنوان جدید
        original_title = task.title.strip()
        new_title = f"ادامه (دور {next_round}): {original_title}"[:200]

        # تجمیع done/remaining/next_actions
        done_parts = report.done_parts or []
        remaining = report.remaining_parts or []
        next_actions = report.next_actions or []
        verifier_summary = (report.summary or "").strip()

        # اگر remaining خالی است، از next_actions به‌عنوان AC استفاده کن
        new_ac = list(remaining) if remaining else list(next_actions)
        if not new_ac:
            # fallback: AC های قبلی task که هنوز برآورده نشده‌اند
            new_ac = list(task.acceptance_criteria or [])
        if not new_ac:
            new_ac = ["تکمیل کامل خواسته‌های اصلی تسک"]

        # description مفصل
        desc_parts: List[str] = []
        desc_parts.append(
            f"این پرامپت برای **دور {next_round}** ادامهٔ کار است. "
            "verifier در دور قبلی نشان داد کار به‌طور کامل انجام نشده."
        )
        if done_parts:
            desc_parts.append(
                "✅ بخش‌هایی که در دور قبل انجام شد:\n"
                + "\n".join(f"  - {p}" for p in done_parts[:10])
            )
        if remaining:
            desc_parts.append(
                "⏳ بخش‌هایی که هنوز باقی مانده (تمرکز روی این‌ها):\n"
                + "\n".join(f"  - {p}" for p in remaining[:10])
            )
        if verifier_summary:
            desc_parts.append(f"📝 خلاصهٔ verifier:\n{verifier_summary[:500]}")
        if next_actions:
            desc_parts.append(
                "🪜 اقدامات بعدی پیشنهادی verifier:\n"
                + "\n".join(f"  - {a}" for a in next_actions[:8])
            )
        # ارجاع به PR قبلی (اگر موجود)
        prev_pr = (task.applied_evidence or {}).get("pr_url") if task.applied_evidence else ""
        prev_branch = (task.applied_evidence or {}).get("pr_branch") if task.applied_evidence else ""
        if prev_pr:
            desc_parts.append(
                f"🔗 PR قبلی: {prev_pr}"
                + (f" (شاخه: `{prev_branch}`)" if prev_branch else "")
                + "\nاگر منطقی است، کار را روی همان شاخه ادامه بده "
                "(یا commit جدید روی main اگر merge شده)."
            )
        new_description = "\n\n".join(desc_parts)

        # target_locations: قبلی + جدیدها از evidence.files
        old_locations: List[Dict[str, Any]] = []
        try:
            old_locations = extract_target_locations(task.prompt or "") or []
        except Exception:
            old_locations = []
        if not old_locations and task.target_files:
            old_locations = [{"path": p} for p in task.target_files]

        # paths جدید از evidence
        evidence_files: List[str] = []
        try:
            ef = (report.evidence or {}).get("files") if isinstance(report.evidence, dict) else None
            if isinstance(ef, list):
                evidence_files = [p for p in ef if isinstance(p, str) and "/" in p]
        except Exception:
            evidence_files = []

        # ادغام بدون duplicate
        seen_paths = {l.get("path") for l in old_locations if isinstance(l, dict)}
        merged_locations = list(old_locations)
        for ep in evidence_files:
            if ep not in seen_paths:
                merged_locations.append({
                    "path": ep,
                    "note": f"از evidence verifier در دور {next_round - 1}",
                })
                seen_paths.add(ep)

        # related_files از پرامپت قبلی (best-effort — استخراج ساده)
        # build_strong_prompt آن را بدون ساختار rich می‌گیرد ولی اگر هیچ
        # نداشتیم کافی است
        related_files: List[Dict[str, Any]] = []

        # tech_context: از description یا watched.user_notes
        tech_context = ""
        if watched and watched.user_notes:
            tech_context = (watched.user_notes or "").strip()[:300]

        # validation_commands: از پرامپت قبلی استخراج کن (regex ساده)
        validation_commands: List[str] = []
        try:
            import re as _re
            m = _re.search(
                r"##\s*\S*\s*دستورات اعتبارسنجی[^\n]*\n(.+?)(?=\n##|\Z)",
                task.prompt or "",
                _re.DOTALL,
            )
            if m:
                for ln in m.group(1).splitlines():
                    s = ln.strip().lstrip("-").strip().strip("`").strip()
                    if s and not s.startswith("_") and len(s) < 200:
                        validation_commands.append(s)
        except Exception:
            pass

        # risks: next_actions به‌عنوان hint چه چیزی ممکن است بشکند
        risks_text = ""
        if next_actions:
            risks_text = (
                "موارد زیر در دور قبل ناقص ماندند — مراقب رگرشن باش:\n"
                + "\n".join(f"  - {a}" for a in next_actions[:5])
            )

        # ساخت پرامپت قوی با ساختار غنی
        try:
            new_prompt = build_strong_prompt(
                title=new_title,
                user_goal=(watched.user_notes if watched else "") or "",
                description=new_description,
                proposed_action="پیاده‌سازی AC های باقی‌مانده با حفظ کارهای انجام‌شدهٔ دور قبل.",
                target_locations=merged_locations,
                related_files=related_files,
                dependency_summary="",
                tech_context=tech_context,
                before_after_examples=[],
                validation_commands=validation_commands,
                acceptance_criteria=new_ac,
                risks=risks_text,
                type_=task.type or "other",
                priority=task.priority or "medium",
                estimate="medium",
            )
        except Exception as _e:
            logger.warning(f"build_strong_prompt for follow-up failed: {_e}")
            return None

        return new_prompt

    async def apply_followup_after_verify(
        self,
        task_id: str,
        report: "OversightReport",
    ) -> None:
        """پس از verify، followup prompt را روی task ست (یا پاک) می‌کند.

        این تابع از verifier بعد از append history فراخوانی می‌شود.
        مسئول _save_tasks هم خودش است (atomic).
        """
        async with self._lock:
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task is None:
                return
            watched = self._find_watched(task.watched_id) if task.watched_id else None

        # generate (خارج از lock چون می‌تواند طولانی باشد — ولی build_strong_prompt
        # سریع است؛ با این حال احتیاط)
        if report.status == "done":
            # موفق — followup را reset کن
            async with self._lock:
                task.followup_prompt = ""
                task.followup_generated_at = None
                task.followup_target_locations = []
                task.followup_acceptance_criteria = []
                task.followup_round = 0
                task.updated_at = now_iso()
                self._save_tasks()
            return

        # غیر-done: followup بساز
        try:
            new_prompt = await self.generate_followup_prompt_for_task(task, report, watched)
        except Exception as _e:
            logger.warning(f"generate_followup_prompt failed: {_e}")
            new_prompt = None

        if not new_prompt:
            return

        # extract معیارها و locations از پرامپت تولید شده
        try:
            from .oversight_strong_prompt import (
                extract_target_locations,
                extract_acceptance_criteria,
            )
            extracted_locs = extract_target_locations(new_prompt) or []
            extracted_ac = extract_acceptance_criteria(new_prompt) or []
        except Exception:
            extracted_locs = []
            extracted_ac = []

        async with self._lock:
            # 🆕 (audit fix) integration با prompt_history:
            # نسخهٔ قبلی task.prompt را به history منتقل کن (archive)
            # و followup را به‌عنوان task.prompt جدید قرار بده — تا کاربر
            # وقتی روی «📋 کپی پرامپت» کلیک کرد، نسخهٔ به‌روز شده را ببیند
            # نه نسخهٔ اولیه که بخشی از آن قبلاً انجام شده.
            history_entry = {
                "prompt": task.prompt,
                "raw_idea": task.raw_idea or "",
                "model_id": (task.models_used[0] if task.models_used else "") or "",
                "generated_at": task.updated_at or task.created_at,
                "source": f"followup_round_{(task.followup_round or 0) + 1}",
            }
            task.prompt_history.insert(0, history_entry)
            task.prompt_history = task.prompt_history[:10]  # cap
            # جایگزین prompt اصلی با followup
            task.prompt = new_prompt
            if extracted_locs:
                task.target_files = [
                    l.get("path", "") for l in extracted_locs if l.get("path")
                ] or task.target_files
            if extracted_ac:
                task.acceptance_criteria = extracted_ac
            # field‌های followup همچنان نگه‌داشته می‌شوند برای backward compat
            # با UI قدیمی (دکمهٔ «اجرای followup»)، ولی prompt اصلی به‌روز است.
            task.followup_prompt = new_prompt
            task.followup_generated_at = now_iso()
            task.followup_target_locations = extracted_locs
            task.followup_acceptance_criteria = extracted_ac
            task.followup_round = (task.followup_round or 0) + 1
            task.updated_at = now_iso()

            # 🆕 (auto-loop) — ping-pong scheduler-driven:
            # اگر watched.auto_continue_until_done فعال است + autonomy=auto +
            # هنوز به max_auto_loop_rounds نرسیدیم → status را به pending
            # برگردان تا scheduler tick بعدی این تسک را دوباره اجرا کند.
            try:
                if (
                    watched
                    and getattr(watched, "auto_continue_until_done", False)
                    and watched.autonomy_level == "auto"
                    and not getattr(watched, "verify_only_mode", False)
                    and task.execution_mode in ("auto_via_projects_page", "auto_via_pr")
                ):
                    max_rounds = int(getattr(watched, "max_auto_loop_rounds", 5) or 5)
                    if (task.followup_round or 0) < max_rounds:
                        task.status = "pending"
                        # next_run_at به الان ست می‌شود تا در tick بعدی اجرا شود
                        task.next_run_at = now_iso()
                        logger.info(
                            f"auto-loop: task {task.id} → pending for round "
                            f"{task.followup_round}/{max_rounds}"
                        )
                    else:
                        logger.info(
                            f"auto-loop: task {task.id} به max_auto_loop_rounds={max_rounds} رسید"
                            f" — متوقف شد (نیاز به مداخلهٔ کاربر)"
                        )
            except Exception as _e:
                logger.debug(f"auto-loop check failed: {_e}")

            self._save_tasks()

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
        """یک نوبت اجرای scheduler. سه نوع کار: scan، run، verify."""
        now = datetime.now(timezone.utc)
        ran: List[str] = []
        scanned: List[str] = []
        verified: List[str] = []
        max_runs = int(self.settings.get("max_parallel_runs") or 2)

        for w in list(self.watched):
            # ----- 1) Scan دوره‌ای -----
            try:
                if w.scan_interval_hours and w.scan_interval_hours > 0:
                    last_scan = (
                        datetime.fromisoformat(w.last_scan_at)
                        if w.last_scan_at
                        else None
                    )
                    if last_scan is None or (now - last_scan) >= timedelta(
                        hours=w.scan_interval_hours
                    ):
                        if w.schedule_enabled:
                            try:
                                # 🆕 (P1) auto-scan از run_deep_scan استفاده می‌کند
                                # نه scan_project ساده — تا تمام ۱۰+ pass + scan_depth
                                # + scan_criteria_weights + selected_models اعمال شوند
                                from .oversight_deep_scan_service import run_deep_scan
                                model_ids = list(getattr(w, "selected_models", []) or [])
                                primary_model = model_ids[0] if model_ids else None
                                await run_deep_scan(
                                    w.id,
                                    model_id=primary_model,
                                    model_ids=model_ids if len(model_ids) > 1 else None,
                                )
                                w.last_scan_at = now.isoformat()
                                w.next_scan_at = (
                                    now + timedelta(hours=w.scan_interval_hours)
                                ).isoformat()
                                scanned.append(w.id)
                            except Exception as e:
                                logger.warning(f"auto-scan {w.id} failed: {e}")
            except Exception as e:
                logger.warning(f"scan check {w.id} failed: {e}")

            # ----- 2) Verify دوره‌ای (مستقل از execution) -----
            try:
                vh = float(getattr(w, "verify_interval_hours", 0) or 0)
                if vh > 0:
                    last_verify = (
                        datetime.fromisoformat(w.last_verify_at)
                        if getattr(w, "last_verify_at", None)
                        else None
                    )
                    if last_verify is None or (now - last_verify) >= timedelta(hours=vh):
                        # تسک‌های نیازمند verify
                        candidates = [
                            t for t in self.tasks
                            if t.watched_id == w.id
                            and t.verification_status
                            in (
                                "pending",
                                "applied_externally_pending_verify",
                                "partial",
                                "regressed",
                            )
                            and t.status not in ("done", "cancelled")
                        ]
                        # اولویت: applied_externally_pending_verify اول
                        candidates.sort(
                            key=lambda t: (
                                0 if t.verification_status == "applied_externally_pending_verify" else 1,
                                {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(t.priority, 9),
                            )
                        )
                        for t in candidates[:max_runs]:
                            try:
                                from .oversight_verifier import verify_task as _verify_task
                                await _verify_task(t.id, model_id=None, triggered_by="scheduler")
                                verified.append(t.id)
                            except Exception as e:
                                logger.warning(f"scheduled verify {t.id} failed: {e}")
                        w.last_verify_at = now.isoformat()
                        w.next_verify_at = (now + timedelta(hours=vh)).isoformat()
            except Exception as e:
                logger.warning(f"verify tick {w.id} failed: {e}")

            # ----- 3) اجرای تسک‌های pending (مسیر A — auto execution) -----
            if not w.schedule_enabled:
                continue
            # فقط اگر autonomy_level=auto و execution_mode auto_via_*
            if w.autonomy_level != "auto" or getattr(w, "verify_only_mode", False):
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

            pending = [
                t for t in self.tasks
                if t.watched_id == w.id and t.status == "pending"
                and t.execution_mode in ("auto_via_projects_page", "auto_via_pr")
            ]
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

        # ----- 4) Daily report (مستقل از scan/run/verify) -----
        # هر بار tick، چک می‌کنیم آیا الان ساعت target است و امروز ارسال نشده
        daily_sent = False
        try:
            from .notification_service import notification_service
            prefs = notification_service.get_prefs()
            daily = prefs.get("daily_report", {}) or {}
            if daily.get("enabled", True):
                tz_name = daily.get("timezone", "Asia/Tehran") or "Asia/Tehran"
                target_hour = int(daily.get("hour_of_day", 8) or 8)
                last_sent = daily.get("last_sent_at")
                try:
                    from zoneinfo import ZoneInfo
                    local_now = datetime.now(ZoneInfo(tz_name))
                except Exception:
                    local_now = datetime.now()
                is_target_hour = local_now.hour == target_hour
                already_sent_today = False
                if last_sent:
                    try:
                        last_dt = datetime.fromisoformat(last_sent)
                        already_sent_today = last_dt.date() == local_now.date()
                    except Exception:
                        already_sent_today = False
                if is_target_hour and not already_sent_today:
                    try:
                        summary = await self.compute_global_health_summary()
                        results = await notification_service.send_daily_report(summary)
                        ok = any(r.get("ok") for r in results) if results else False
                        notification_service.update_prefs({
                            "daily_report": {
                                "last_sent_at": local_now.isoformat(),
                                "last_sent_status": "ok" if ok else "no_channel_ready",
                            }
                        })
                        daily_sent = True
                        logger.info(f"daily_report sent: {ok}, channels={len(results)}")
                    except Exception as e:
                        logger.warning(f"daily_report failed: {e}")
                        try:
                            notification_service.update_prefs({
                                "daily_report": {
                                    "last_sent_at": local_now.isoformat(),
                                    "last_sent_status": f"failed: {str(e)[:200]}",
                                }
                            })
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"daily_report check skipped: {e}")

        return {
            "ran": ran,
            "ran_count": len(ran),
            "scanned": scanned,
            "scanned_count": len(scanned),
            "daily_report_sent": daily_sent,
            "verified": verified,
            "verified_count": len(verified),
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
