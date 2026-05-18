"""Verify v6 — context_builder

ساخت VerifyContext یکپارچه که شامل همه‌ی state لازم برای یک verify run است:
task, watched, raw_idea, prompt, prompt_history, verify_history,
consolidation_meta, merged_source_tasks, scan_metadata, repo_tree,
commits_recent + کش‌های in-memory و trace observability.

طبق Bug C6 v2 — گپ ۱ (حافظهٔ تکه‌تکه vs کامل).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..oversight_service import OversightTask, WatchedProject

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VerifyConfig — تنظیمات متمرکز (بهبود ۹ — کاستی ۵ در v2)
# ---------------------------------------------------------------------------


@dataclass
class VerifyConfig:
    """تنظیمات متمرکز برای verify v6.

    اگر WatchedProject.verify_v6_config برابر None باشد، defaults استفاده
    می‌شود. اگر مقادیر out-of-range باشند، clamp به range معتبر اعمال
    می‌شود (edge case v2 — config validation).
    """
    # iteration limits
    max_iterations: int = 3
    iter1_confidence_threshold: float = 0.8
    iter2_confidence_threshold: float = 0.7

    # content grep
    enable_content_grep: bool = True
    max_files_per_run: int = 50
    max_file_size_bytes: int = 500_000
    max_identifiers_per_ac: int = 15
    iter2_max_extra_files: int = 50
    iter2_max_identifiers: int = 25

    # model tier (strong_pref chain)
    strong_model_preference: List[str] = field(default_factory=lambda: [
        "gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6",
    ])

    # cache (بهبود ۷)
    enable_ac_cache: bool = True
    ac_cache_max_age_days: int = 7
    ac_cache_consecutive_threshold: int = 3

    # confidence weights (گپ ۶)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "content_grep_strong": 3.0,
        "content_grep_weak": 1.5,
        "code_aware_basename": 1.0,
        "playwright": 2.0,
        "ai_verifier": 1.0,
        "vision_frontend": 0.5,
        "vision_backend": 0.0,
        "strong_model": 2.5,
    })

    # observability (بهبود ۸)
    enable_trace: bool = True
    trace_max_entries: int = 1000

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "VerifyConfig":
        """ساخت VerifyConfig از dict (مثلاً WatchedProject.verify_v6_config).

        مقادیر out-of-range را clamp می‌کند تا verify از کار نیفتد.
        """
        if not isinstance(data, dict):
            return cls()
        cfg = cls()
        _clamp_int = lambda v, lo, hi, default: max(lo, min(hi, int(v))) if isinstance(v, (int, float)) and not isinstance(v, bool) else default
        _clamp_float = lambda v, lo, hi, default: max(lo, min(hi, float(v))) if isinstance(v, (int, float)) and not isinstance(v, bool) else default

        cfg.max_iterations = _clamp_int(data.get("max_iterations"), 1, 10, cfg.max_iterations)
        cfg.iter1_confidence_threshold = _clamp_float(data.get("iter1_confidence_threshold"), 0.0, 1.0, cfg.iter1_confidence_threshold)
        cfg.iter2_confidence_threshold = _clamp_float(data.get("iter2_confidence_threshold"), 0.0, 1.0, cfg.iter2_confidence_threshold)
        if isinstance(data.get("enable_content_grep"), bool):
            cfg.enable_content_grep = data["enable_content_grep"]
        cfg.max_files_per_run = _clamp_int(data.get("max_files_per_run"), 1, 500, cfg.max_files_per_run)
        cfg.max_file_size_bytes = _clamp_int(data.get("max_file_size_bytes"), 1024, 10_000_000, cfg.max_file_size_bytes)
        cfg.max_identifiers_per_ac = _clamp_int(data.get("max_identifiers_per_ac"), 1, 100, cfg.max_identifiers_per_ac)
        cfg.iter2_max_extra_files = _clamp_int(data.get("iter2_max_extra_files"), 0, 500, cfg.iter2_max_extra_files)
        cfg.iter2_max_identifiers = _clamp_int(data.get("iter2_max_identifiers"), 1, 100, cfg.iter2_max_identifiers)
        if isinstance(data.get("strong_model_preference"), list):
            cfg.strong_model_preference = [str(x) for x in data["strong_model_preference"]][:10]
        if isinstance(data.get("enable_ac_cache"), bool):
            cfg.enable_ac_cache = data["enable_ac_cache"]
        cfg.ac_cache_max_age_days = _clamp_int(data.get("ac_cache_max_age_days"), 1, 365, cfg.ac_cache_max_age_days)
        cfg.ac_cache_consecutive_threshold = _clamp_int(data.get("ac_cache_consecutive_threshold"), 1, 20, cfg.ac_cache_consecutive_threshold)
        if isinstance(data.get("weights"), dict):
            for k, v in data["weights"].items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cfg.weights[str(k)] = max(0.0, min(10.0, float(v)))
        if isinstance(data.get("enable_trace"), bool):
            cfg.enable_trace = data["enable_trace"]
        cfg.trace_max_entries = _clamp_int(data.get("trace_max_entries"), 10, 10_000, cfg.trace_max_entries)
        return cfg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "iter1_confidence_threshold": self.iter1_confidence_threshold,
            "iter2_confidence_threshold": self.iter2_confidence_threshold,
            "enable_content_grep": self.enable_content_grep,
            "max_files_per_run": self.max_files_per_run,
            "max_file_size_bytes": self.max_file_size_bytes,
            "max_identifiers_per_ac": self.max_identifiers_per_ac,
            "iter2_max_extra_files": self.iter2_max_extra_files,
            "iter2_max_identifiers": self.iter2_max_identifiers,
            "strong_model_preference": list(self.strong_model_preference),
            "enable_ac_cache": self.enable_ac_cache,
            "ac_cache_max_age_days": self.ac_cache_max_age_days,
            "ac_cache_consecutive_threshold": self.ac_cache_consecutive_threshold,
            "weights": dict(self.weights),
            "enable_trace": self.enable_trace,
            "trace_max_entries": self.trace_max_entries,
        }


# ---------------------------------------------------------------------------
# VerifyContext — ساختار اصلی state (گپ ۱)
# ---------------------------------------------------------------------------


@dataclass
class VerifyContext:
    """ساختار state یکپارچه برای یک verify run.

    در ابتدای verify_task() ساخته می‌شود و در همهٔ probes پاس داده می‌شود.
    کش‌های in-memory و trace per-verify-run هستند (بین runها به اشتراک
    گذاشته نمی‌شوند).
    """
    task: Any                                  # OversightTask — ref فقط
    watched: Optional[Any]                     # WatchedProject — ref فقط
    raw_idea_full: str = ""                    # cap 50KB
    prompt_full: str = ""                      # cap 100KB
    task_steps_full: List[Dict[str, Any]] = field(default_factory=list)
    prompt_history: List[Dict[str, Any]] = field(default_factory=list)   # آخرین ۳
    verify_history: List[Dict[str, Any]] = field(default_factory=list)   # آخرین ۵
    consolidation_meta: Optional[Dict[str, Any]] = None
    merged_source_tasks: List[Dict[str, Any]] = field(default_factory=list)  # cap 30
    scan_metadata: Optional[Dict[str, Any]] = None
    repo_tree: List[str] = field(default_factory=list)                   # cap 5000
    commits_recent: List[Dict[str, Any]] = field(default_factory=list)   # cap 50

    # per-verify-run caches
    file_content_cache: Dict[str, str] = field(default_factory=dict)
    file_grep_cache: Dict[Tuple[str, str], List[Dict[str, Any]]] = field(default_factory=dict)

    # observability (بهبود ۸)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    config: VerifyConfig = field(default_factory=VerifyConfig)
    files_fetched_count: int = 0
    grep_calls_count: int = 0
    ai_calls_count: int = 0

    def append_trace(self, entry: Dict[str, Any]) -> None:
        """append یک رویداد trace با enforce سقف trace_max_entries (FIFO)."""
        if not self.config.enable_trace:
            return
        self.trace.append(entry)
        cap = max(10, self.config.trace_max_entries)
        if len(self.trace) > cap:
            # حذف oldest (FIFO) — edge case v2: trace size cap
            del self.trace[:len(self.trace) - cap]


# ---------------------------------------------------------------------------
# build_verify_context — entry-point
# ---------------------------------------------------------------------------


_RAW_IDEA_CAP = 50_000
_PROMPT_CAP = 100_000
_PROMPT_HISTORY_KEEP = 3
_VERIFY_HISTORY_KEEP = 5
_MERGED_SOURCE_CAP = 30
_REPO_TREE_CAP = 5000
_COMMITS_RECENT_CAP = 50

# cache برای repo_tree (روی sha) — به اشتراک گذاشته شده بین verify run های
# همان repo (نه per-task). کلید: f"{repo_full_name}@{sha}"
_REPO_TREE_CACHE: Dict[str, List[str]] = {}


async def build_verify_context(
    task: Any,
    watched: Optional[Any],
    *,
    config: Optional[VerifyConfig] = None,
) -> VerifyContext:
    """ساخت VerifyContext از task + watched + config.

    - caps را روی فیلدهای متنی و لیستی اعمال می‌کند.
    - repo_tree یک‌بار از GitHub fetch می‌شود (با cache روی sha).
    - در ابتدای verify_task() صدا زده می‌شود.
    """
    cfg = config or VerifyConfig()

    raw_idea = (getattr(task, "raw_idea", "") or "")[:_RAW_IDEA_CAP]
    prompt_full = (getattr(task, "prompt", "") or "")[:_PROMPT_CAP]
    task_steps = list(getattr(task, "task_steps", None) or [])
    prompt_history = list(getattr(task, "prompt_history", None) or [])[-_PROMPT_HISTORY_KEEP:]
    verify_history = list(getattr(task, "verification_history", None) or [])[-_VERIFY_HISTORY_KEEP:]
    consolidation_meta = getattr(task, "consolidation_meta", None)
    scan_metadata = getattr(task, "created_by_scan_metadata", None)

    # merged_source_tasks — اگر super-task باشد، top-N by priority
    merged_source_tasks: List[Dict[str, Any]] = []
    merged_from_snapshot = getattr(task, "merged_from_snapshot", None) or {}
    if isinstance(merged_from_snapshot, dict) and merged_from_snapshot:
        items = list(merged_from_snapshot.values())
        # sort by priority (critical > high > medium > low)
        prio_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: prio_rank.get(str(x.get("priority", "medium")), 9))
        merged_source_tasks = items[:_MERGED_SOURCE_CAP]

    # repo_tree fetch (با cache روی sha) — graceful اگر network/token نباشد
    repo_tree: List[str] = []
    commits_recent: List[Dict[str, Any]] = []
    repo_full_name = ""
    if watched is not None:
        repo_full_name = getattr(watched, "repo_full_name", "") or ""
    if not repo_full_name:
        repo_full_name = getattr(task, "project_full_name", "") or ""

    if repo_full_name and "/" in repo_full_name:
        try:
            repo_tree, commits_recent = await _fetch_repo_tree_and_commits(repo_full_name, cfg)
        except Exception as _e:
            logger.warning(f"build_verify_context: repo_tree fetch failed: {_e}")
            repo_tree = []
            commits_recent = []

    repo_tree = repo_tree[:_REPO_TREE_CAP]
    commits_recent = commits_recent[:_COMMITS_RECENT_CAP]

    ctx = VerifyContext(
        task=task,
        watched=watched,
        raw_idea_full=raw_idea,
        prompt_full=prompt_full,
        task_steps_full=task_steps,
        prompt_history=prompt_history,
        verify_history=verify_history,
        consolidation_meta=consolidation_meta,
        merged_source_tasks=merged_source_tasks,
        scan_metadata=scan_metadata,
        repo_tree=repo_tree,
        commits_recent=commits_recent,
        config=cfg,
    )
    ctx.append_trace({
        "phase": "build_verify_context",
        "task_id": getattr(task, "id", ""),
        "repo": repo_full_name,
        "repo_tree_size": len(repo_tree),
        "commits_recent": len(commits_recent),
        "merged_source_tasks": len(merged_source_tasks),
        "config_summary": {
            "max_iterations": cfg.max_iterations,
            "enable_ac_cache": cfg.enable_ac_cache,
            "enable_trace": cfg.enable_trace,
        },
    })
    return ctx


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def _fetch_repo_tree_and_commits(
    repo_full_name: str,
    cfg: VerifyConfig,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """fetch repo_tree و recent commits از GitHub. graceful on failure.

    cache روی sha repo (به اشتراک بین verify runها). اگر token نبود یا
    rate limit بود، list خالی برمی‌گرداند.
    """
    try:
        from ..github_storage import get_github_token
    except Exception:
        get_github_token = lambda: ""  # type: ignore

    try:
        from ..oversight_verifier import _fetch_recent_commits  # type: ignore
    except Exception:
        _fetch_recent_commits = None  # type: ignore

    token = ""
    try:
        token = get_github_token() or ""
    except Exception:
        token = ""

    if not token:
        return [], []

    # دریافت HEAD sha برای cache key
    try:
        import httpx
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/branches/main",
                headers=headers,
            )
            if r.status_code != 200:
                # fallback: master
                r = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}/branches/master",
                    headers=headers,
                )
            head_sha = ""
            if r.status_code == 200:
                head_sha = (r.json().get("commit") or {}).get("sha", "") or ""

            cache_key = f"{repo_full_name}@{head_sha}" if head_sha else ""
            if cache_key and cache_key in _REPO_TREE_CACHE:
                cached = _REPO_TREE_CACHE[cache_key]
                commits: List[Dict[str, Any]] = []
                if _fetch_recent_commits is not None:
                    try:
                        commits = await _fetch_recent_commits(repo_full_name, token, limit=_COMMITS_RECENT_CAP)
                    except Exception:
                        commits = []
                return cached, commits

            if not head_sha:
                return [], []

            tree_resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/git/trees/{head_sha}?recursive=1",
                headers=headers,
            )
            if tree_resp.status_code != 200:
                return [], []
            data = tree_resp.json()
            entries = data.get("tree") or []
            paths = [str(e.get("path", "")) for e in entries if e.get("type") == "blob"]
            paths = paths[:_REPO_TREE_CAP]
            if cache_key:
                _REPO_TREE_CACHE[cache_key] = paths

            commits: List[Dict[str, Any]] = []
            if _fetch_recent_commits is not None:
                try:
                    commits = await _fetch_recent_commits(repo_full_name, token, limit=_COMMITS_RECENT_CAP)
                except Exception:
                    commits = []
            return paths, commits
    except Exception as _e:
        logger.warning(f"_fetch_repo_tree_and_commits failed for {repo_full_name}: {_e}")
        return [], []


__all__ = ["VerifyContext", "VerifyConfig", "build_verify_context"]
