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
from typing import Any, Dict, List, Optional, Tuple
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
# 🆕 (auto-discover blocklist) — repo هایی که کاربر صریحاً از watched
# حذف کرده. auto_discover scheduler از این لیست رد می‌شود تا دوباره
# add نکند. وقتی کاربر دستی repo را add می‌کند، از این لیست حذف می‌شود.
REMOVED_WATCHED_FILE = STORAGE_DIR / "removed_watched.json"
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
    # 🆕 (Phase 4) — حالت verify: deep (پیش‌فرض، با probe/vision/code-aware/
    # backend-log/smart-nav) یا fast (فقط grep+AI، سریع‌تر ولی شواهد کمتر)
    # این flag هم در scheduler خودکار و هم در دکمه‌ی verify-now استفاده می‌شود.
    verify_mode: str = "deep"  # "deep" | "fast"
    # 🆕 (Phase 5) — Scan V5: comprehensive inventory + purpose + delta + logic
    last_scan_inventory: Optional[Dict[str, Any]] = None
    last_scan_purpose_map: Optional[Dict[str, Any]] = None
    last_scan_at_v5: Optional[str] = None
    prev_scan_state: Optional[Dict[str, Any]] = None  # {path: sha,size,...}
    # حالت‌های scan v5 (همه default sensible)
    stale_detection_enabled: bool = True
    delta_analysis_enabled: bool = True
    runtime_discovery_enabled: bool = True
    outcome_data_enabled: bool = True
    logic_audit_enabled: bool = True
    notification_audit_enabled: bool = True
    inspector_session_enabled: bool = True  # R14
    auto_task_checklist_mode: str = "auto"  # "auto" | "always" | "never"  R5
    cleanup_tasks_enabled: bool = True
    auto_task_notify_sound: bool = False  # R6 — silent default
    scan_notify_sound: bool = False  # R6
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
    # 🆕 (Prompt-GitHub Sync) — اگر True، تسک‌های این پروژه به
    # ریپوی همین پروژه (در پوشهٔ prompt/) sync می‌شوند تا ابزارهای خارجی
    # (Cloud Code و …) بتوانند آن‌ها را به‌ترتیب اولویت اجرا کنند.
    # default True — برای همه‌ی پروژه‌های فعلی و آینده فعال است.
    prompt_sync_enabled: bool = True
    # شاخه‌ای که فایل‌های prompt در آن نگه‌داری می‌شوند (پیش‌فرض = default_branch)
    prompt_sync_branch: Optional[str] = None
    # 🆕 (Claude Auto-Runner) — اگر True، فایل
    # `.github/workflows/claude-auto-task.yml` روی این ریپو نصب شده و
    # secret های مورد نیاز ست شده‌اند. هر تغییری در prompt/_index.json یا
    # prompt/*.md کاربر را به اجرای خودکار Claude Code (headless) می‌برد
    # که تسک‌های pending را از /api/external/prompts/ می‌گیرد، اجرا می‌کند
    # و مستقیماً به main commit/push می‌کند. هیچ تعامل دستی لازم نیست.
    claude_runner_enabled: bool = False
    claude_runner_installed_at: Optional[str] = None
    claude_runner_last_error: Optional[str] = None
    # workflow کجا نصب شد (مسیر در ریپو)؛ صرفاً diagnostic
    claude_runner_workflow_path: Optional[str] = None
    # 🆕 (verify-after-complete lock) — وقتی Claude یک تسک را /complete می‌زند،
    # تسک وارد فاز verify می‌شود. در این مدت، **هیچ workflow_dispatch جدیدی
    # برای این watched نباید trigger شود** حتی اگر فولدر prompt/ تغییر کند
    # (تسک جدید، حذف، sync). این lock تمرکز روی همان تسک را تضمین می‌کند.
    # وقتی verify تمام شد (done/partial→retry/failed), lock پاک می‌شود.
    # stale-detection: اگر lock بیش از 30 دقیقه قدیمی شد، خودکار پاک می‌شود
    # (در صورت crash backend در میانه verify).
    claude_runner_verifying_task_id: Optional[str] = None
    claude_runner_verifying_started_at: Optional[str] = None
    # شمارش retry های auto-runner برای رسیدن به max
    claude_runner_max_retries_per_task: int = 3
    # 🆕 (auto-loop) ping-pong scheduler-driven:
    # اگر فعال، پس از verify=partial scheduler خودکار:
    #   1. status تسک به pending برمی‌گردد
    #   2. apply‌ٔ مجدد با followup_prompt
    #   3. verify خودکار
    # تا verify=done شود یا max_auto_loop_rounds برسد یا regress رخ دهد
    # فقط وقتی autonomy_level=auto و execution_mode auto_via_* معنی دارد
    auto_continue_until_done: bool = False
    max_auto_loop_rounds: int = 5
    # 🆕 (Smart Task Lifecycle) بازتولید خودکار پرامپت‌های ناقص قدیمی
    # وقتی scan خودکار اجرا می‌شود، پس از scan تسک‌هایی که prompt_quality_score آن‌ها
    # کمتر از prompt_quality_threshold باشد بازتولید می‌شوند (با rate-limit 5).
    auto_regenerate_old_prompts: bool = False
    prompt_quality_threshold: int = 60  # 0..100
    last_prompt_audit_at: Optional[str] = None
    # 🆕 (Smart Task Lifecycle) فعال‌سازی dedup در ایجاد دستی + آستانهٔ امتیاز
    dedup_in_manual_create: bool = True
    dedup_score_threshold: float = 0.65  # 0..1

    # 🔬 (Runtime Verify Stage 4) — base URLs برای probe های runtime
    # اگر تنظیم نشده باشد، UI/API probe ها برای این پروژه skip می‌شوند.
    frontend_base_url: Optional[str] = None  # مثلاً https://ai-creator-frontend.onrender.com
    backend_base_url: Optional[str] = None   # مثلاً https://ai-creator-backend.onrender.com
    # احراز هویت برای probe ها — dict {"type": "bearer"|"cookie", "value": "..."}
    # نمونه: {"type": "cookie", "value": "session=abc; csrf=xyz"}
    runtime_auth: Optional[Dict[str, Any]] = None
    # path مطلق به repo (clone شده) برای static + test probe
    # اگر None، probe های static/backend_test skip می‌شوند
    runtime_repo_path: Optional[str] = None
    # 🔬 (Auto-detect) — اگر URL ها از Render auto-detect شدند، اینجا
    # علامت می‌خوریم. کاربر می‌تواند manually override کند.
    runtime_autodetected: bool = False
    # نتیجهٔ آخرین تست اتصال — {frontend: {ok, status, error?}, backend: {...}, at: ISO}
    runtime_connection_test: Optional[Dict[str, Any]] = None
    # 🔐 (Phase 3) — auth recipe برای probe ها
    # اگر تنظیم شد، قبل از هر verify run یک login flow اجرا می‌شود و
    # storage_state (cookies + localStorage) برای استفاده‌ی probe ها
    # ذخیره می‌شود. ساختار:
    # {
    #   "type": "form_login",
    #   "login_url": "/login",
    #   "steps": [
    #     {"action": "fill", "selector": "input[name=email]", "value_env": "TEST_EMAIL"},
    #     {"action": "fill", "selector": "input[name=password]", "value_env": "TEST_PASSWORD"},
    #     {"action": "click", "selector": "button[type=submit]"},
    #     {"action": "wait_for_url", "contains": "/dashboard", "timeout_ms": 5000}
    #   ],
    #   "success_indicator": {"selector": "[data-testid='user-menu']", "must_exist": true},
    #   "session_ttl_minutes": 30
    # }
    runtime_auth_recipe: Optional[Dict[str, Any]] = None
    # cached storage state (encrypted) — توسط auth_runner مدیریت می‌شود
    # {encrypted_blob, expires_at, obtained_at, login_failed_count}
    runtime_storage_state: Optional[Dict[str, Any]] = None

    # 🆕 (C5) — تنظیمات نمایش (pagination, sort, filter, search) برای ۳ تب
    # ساختار:
    # {
    #   "tasks_tab": {page_size, current_page, sort_field, sort_order,
    #                 filters: {...}, search_query},
    #   "archive_tab": {...},
    #   "reports_tab": {...}
    # }
    # هر تب مستقل ذخیره می‌شود. cross-device sync.
    view_preferences: Dict[str, Any] = field(default_factory=dict)

    # 🔬 (Bug C6 — Verify v6, بهبود ۹) Centralized VerifyConfig
    # اگر None، defaults از VerifyConfig.from_dict() استفاده می‌شود.
    # ساختار: VerifyConfig.to_dict() (max_iterations, thresholds,
    # weights, strong_model_preference, ac_cache settings, trace).
    # GET/PATCH /api/oversight/watched/{id}/verify-v6-config
    verify_v6_config: Optional[Dict[str, Any]] = None

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
    type: str = "other"  # idea | bug | feature_request | refactor | docs | reminder | other
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
    # 🔬 (Runtime Verify Stage 1) — AC ساختاریافته. هر AC می‌تواند:
    #   - str قدیمی (backward compat — هنگام load به dict تبدیل می‌شود)
    #   - dict جدید: {text, verify_method, verify_plan, evidence_history, ...}
    # برای جزئیات شکل ساختار، verify_runtime/ac_schema.py را ببین.
    acceptance_criteria: List[Any] = field(default_factory=list)
    # 🆕 followup prompt — وقتی verify نتیجهٔ partial/not_done/regressed/error
    # داد، AI یک پرامپت ادامه (focused on remaining_parts) تولید می‌کند که
    # کاربر می‌تواند کپی یا با دکمهٔ "اجرای بعدی با AI" اعمال کند.
    # وقتی verify='done' شد، این فیلدها reset می‌شوند.
    followup_prompt: str = ""
    followup_generated_at: Optional[str] = None
    followup_target_locations: List[Dict[str, Any]] = field(default_factory=list)
    # 🔬 (Runtime Verify Stage 1) — followup AC هم ساختاریافته
    followup_acceptance_criteria: List[Any] = field(default_factory=list)
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
    # 🆕 (auto-runner abandonment) — وقتی Claude به سقف retry رسید یا verify
    # regressed داد، task آرشیو می‌شود ولی *علتش با success فرق دارد*.
    # این فیلد جدا می‌کند تا UI/گزارش‌ها بدانند:
    #   - "" / None / "done"  → آرشیو معمولی (موفق)
    #   - "max_retries"       → Claude در سقف retry گیر کرد، TO-DO ساخت
    #   - "regressed"         → verify regression پیدا کرد، TO-DO ساخت
    archived_reason: Optional[str] = None
    # ❌ Phase 2 prompt_history duplicate حذف شد — تعریف موجود در خط ۳۰۲
    # (P4) همان نیاز را پوشش می‌دهد. apply_followup_as_new_prompt و
    # revert_prompt_from_history با همان schema هماهنگ شده‌اند.
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
    # 🆕 (Smart Task Lifecycle) merge / quality tracking
    # merge_count: چندبار این تسک با تسک دیگری ادغام شده (manual یا auto)
    merge_count: int = 0
    # raw_idea_history: هربار که تسک از طریق merge یا manual create دیده می‌شود،
    # یک entry append می‌شود — مفید برای audit و forensics.
    # هر آیتم: {ts, source, raw_idea, candidate_title, merged_fields, similarity_score}
    raw_idea_history: List[Dict[str, Any]] = field(default_factory=list)
    # prompt_quality_score: امتیاز 0..100 از _score_prompt_quality — هربار scan
    # یا regenerate به‌روز می‌شود.
    prompt_quality_score: Optional[int] = None
    last_quality_audit_at: Optional[str] = None
    # manual_seen_count: چندبار از طریق manual create به همین تسک ادغام شده
    manual_seen_count: int = 0
    # 🆕 (Multi-pass Checklist) لیست مراحل تسک (از multi-pass plan).
    # هر مرحله یک dict با:
    #   {id, title, scope, raw_excerpt, key_terms,
    #    status: pending|done|partial|not_done|error,
    #    completion_pct: 0-100,
    #    remaining: str (آنچه هنوز باقی مانده),
    #    evidence: str (شواهد از verify),
    #    last_verified_at: ISO,
    #    completed_at: ISO}
    # verify خودکار این فیلدها را به‌روز می‌کند.
    task_steps: List[Dict[str, Any]] = field(default_factory=list)
    # درصد کلی پیشرفت (محاسبه‌شده از مراحل) — اگر task_steps خالی است، None
    overall_completion_pct: Optional[int] = None
    # 🆕 (Inspector → Oversight) reference به context کامل (screenshots/logs/urls)
    # که در inspector_context/{id}.json ذخیره شده. None برای تسک‌های غیر-inspector.
    inspector_context_id: Optional[str] = None
    inspector_mode: Optional[str] = None  # "chat" | "visual_debug" | None
    # 🆕 (Inspector → Oversight) متن meta جدا که در UI کنار پرامپت نمایش داده می‌شود
    # (page_url, captured_at, screenshot timestamps, session id, ...) —
    # مستقل از task.prompt که فقط core است.
    inspector_meta_summary: Optional[str] = None

    # 🆕 (Reminder feature) — فعال فقط زمانی که type=="reminder":
    # reminder_at: ISO datetime زمان firing بعدی (UTC).
    # reminder_state: گردش کار یادآوری.
    #   none      = نوع reminder نیست
    #   scheduled = منتظر firing
    #   fired     = الان firing شده، منتظر پاسخ کاربر (snooze / done / tick)
    #   snoozed   = کاربر snooze زده، reminder_at به آینده رفته
    #   done      = همهٔ آیتم‌ها انجام شدند، archived
    reminder_at: Optional[str] = None
    reminder_state: str = "none"
    # هر آیتم: {ts, action: "scheduled"|"fired"|"snoozed"|"done"|"step_ticked", payload}
    reminder_history: List[Dict[str, Any]] = field(default_factory=list)
    # message_id آخرین پیام یادآوری در تلگرام — برای edit (cross out items)
    reminder_message_id: Optional[int] = None
    # rule تکرار (آینده): "daily" | "weekly" | None
    reminder_repeat_rule: Optional[str] = None

    # 🆕 (Phase 6 — bug C3) Post-Verify Intelligent Task Consolidation
    # وقتی این تسک به‌عنوان source در یک super-task ادغام شد:
    #   merged_into = id همان super-task
    #   archive_reason = "merged_into_consolidated_task"
    #   tags شامل "merged"
    # وقتی این تسک خود یک super-task است:
    #   merged_from = [source_task_id, ...]
    #   merged_from_snapshot = {source_id: کل dict تسک قبل از آرشیو} — برای undo
    #   consolidation_meta = {cluster_theme, rationale, mode, ai_calls_used, ts}
    # source برای super-taskها = "auto_consolidation" (مقدار جدید)
    # 🆕 (C4 fix) — tags برای task هم لازم شد (consolidated, merged, ...).
    # backward-compat: تسک‌های قدیمی بدون tags ذخیره شده‌اند، _filter_known_fields
    # هنگام load عبور می‌دهد و این default [] استفاده می‌شود.
    tags: List[str] = field(default_factory=list)
    # 🆕 (C5) — pin: تسک‌های پین‌شده همیشه بالای لیست. pin در active و archive
    # مستقل است (تسک معمولاً یا یکی یا دیگری) ولی state ذخیره می‌شود.
    pinned: bool = False
    pinned_at: Optional[str] = None
    # 🆕 (C5) — title management:
    # title_history: ts, source (manual|ai_generate|verify_reassess|regenerate|consolidation),
    #               old_title, new_title
    # manual_title_override: اگر True، AI خودکار عنوان را عوض نمی‌کند
    #                       (احترام به ویرایش دستی کاربر)
    title_history: List[Dict[str, Any]] = field(default_factory=list)
    manual_title_override: bool = False
    merged_into: Optional[str] = None
    merged_from: List[str] = field(default_factory=list)
    merged_from_snapshot: Dict[str, Any] = field(default_factory=dict)
    archive_reason: Optional[str] = None
    consolidation_meta: Optional[Dict[str, Any]] = None
    # 🆕 (C3) checklist هوشمند — اگر watched.auto_task_checklist_mode != "never"
    # و difficulty cluster medium/large بود، در super-task ست می‌شود.
    # هر آیتم: {id, text, priority: low|medium|high, done: bool}
    intelligent_checklist: Optional[List[Dict[str, Any]]] = None

    # 🔬 (Bug C6 — Verify v6, بهبود ۷) Per-AC state cache
    # ساختار:
    # {
    #   "<ac_hash>": {
    #     "verdict": "done", "confidence": 0.92,
    #     "last_verified_at": ISO, "files_checksum": "abc123",
    #     "consecutive_done_count": 3, "evidence": ["..."]
    #   }
    # }
    # اگر consecutive_done >= 3 و checksum unchanged و age < 7 days،
    # verify v6 از این cache استفاده می‌کند و probes را skip می‌کند.
    # مدیریت در backend/app/services/verify_runtime/ac_cache_service.py
    ac_verify_cache: Dict[str, Any] = field(default_factory=dict)

    # 🆕 (Prompt-GitHub Sync) — نگاشت تسک ↔ فایل پرامپت در ریپو
    # github_prompt_path: مسیر فایل در ریپو (e.g., "prompt/task-{id}.md")
    # github_prompt_sha: sha فعلی فایل (برای update/delete via Contents API)
    # github_prompt_synced_at: ISO آخرین sync موفق
    # github_prompt_archived: True اگر فایل در prompt/archive/ است
    # github_prompt_last_error: اگر sync fail شد، پیام خطا (برای retry/UI)
    github_prompt_path: Optional[str] = None
    github_prompt_sha: Optional[str] = None
    github_prompt_synced_at: Optional[str] = None
    github_prompt_archived: bool = False
    github_prompt_last_error: Optional[str] = None

    # 🆕 (External Tool / Cloud Code) — اولویت اجرا + قفل اجرا
    # execution_priority: عدد صحیح (کوچک‌تر = اولویت بالاتر). داینامیک recompute.
    # external_status: گردش کار اجرای خارجی
    #   "pending"     = آماده پیک‌آپ
    #   "claimed"     = ابزار خارجی قفل گرفته، در حال اجرا
    #   "in_progress" = ابزار خارجی صراحتاً پیشرفت داده
    #   "done"        = ابزار اعلام تکمیل
    #   "failed"      = ابزار خطا گزارش داد، به pending برمی‌گردد
    # external_locked_by: شناسه ابزار/agent (e.g., "cloud-code-1")
    # external_lease_until: ISO منقضی شدن lease (default 30min)
    # external_attempts: شمارش‌گر تلاش‌ها
    # external_last_error: متن آخرین خطا
    execution_priority: int = 100
    external_status: str = "pending"
    external_locked_by: Optional[str] = None
    external_locked_at: Optional[str] = None
    external_lease_until: Optional[str] = None
    external_attempts: int = 0
    external_last_error: Optional[str] = None

    # 🆕 (Reference Projects) — پروژه‌های منتخب کاربر به‌عنوان منبع الهام
    # کاربر در زمان نوشتن تسک می‌تواند چند پروژهٔ از قبل لود-شده (watched)
    # را به‌عنوان مرجع تیک بزند. در زمان تولید پرامپت، سیستم به این پروژه‌ها
    # مراجعه می‌کند، فایل‌ها و منطق آنها را استخراج/دسته‌بندی می‌کند، و در
    # پرامپت نهایی (با شرایط پروژهٔ فعلی) ادغام می‌کند.
    #
    # هر آیتم: {
    #   "project_id": str,    # watched.id یا repo_full_name
    #   "project_path": str,  # repo_full_name (e.g., "owner/repo")
    #   "is_selected": bool   # درست (selected toggle from UI/Telegram)
    # }
    #
    # default: لیست خالی (تسک از این فیچر استفاده نمی‌کند)
    selected_projects: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ====================================================================
# 🆕 (Smart Task Lifecycle) Similarity & Merge dataclasses
# ====================================================================

@dataclass
class SimilarityMatch:
    """نتیجهٔ یک کاندید مشابه‌سنجی برای یک تسک."""
    task_id: str
    title: str
    score: float  # 0..1 وزن‌دار
    title_jaccard: float
    idea_overlap: float
    ac_overlap: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CreateTaskResult:
    """نتیجهٔ create_task — هم برای ایجاد موفق، هم برای duplicate."""
    status: str  # "created" | "duplicate_detected" | "merged"
    task: Optional[Dict[str, Any]] = None
    similar_matches: List[Dict[str, Any]] = field(default_factory=list)
    merge_preview: Optional[Dict[str, Any]] = None
    message: str = ""

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

    # 🔬 (Bug C6 — Verify v6, بهبود ۸) Observability/Trace mode
    # verify_trace: کل trace decisions (per AC، per iteration)
    # ac_probe_details: per-AC summary (probes اجرا شده، نتایج)
    # verify_version: "v5" | "v6" — برای A/B و backward compat
    # config_used: snapshot از VerifyConfig که در این run استفاده شد
    # endpoint: GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}
    verify_trace: List[Dict[str, Any]] = field(default_factory=list)
    ac_probe_details: List[Dict[str, Any]] = field(default_factory=list)
    verify_version: str = "v5"
    config_used: Dict[str, Any] = field(default_factory=dict)

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
# 🔴 (extraction-100pct-fix v3) — Attachment size thresholds
# قبلاً سه magic number جدا داشتیم: 200_000، 500_000، 500_000.
# حالا یک constant، با dual-tier: "huge" برای step-planner hint،
# "large" برای output budget bump + completeness warning.
# ====================================================================
HUGE_IDEA_CHARS: int = 200_000   # step planner: «attachment غول‌پیکر» — instruction relaxed
LARGE_IDEA_CHARS: int = 500_000  # synthesis: bump output budget + add per-file completeness warning


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
            # 🆕 (Claude Auto-Runner) — وقتی True، پروژه‌های جدیدی که اضافه
            # می‌شوند (manual یا auto-discover) خودکار با Claude Runner
            # bootstrap می‌شوند. اگر CLAUDE_CODE_OAUTH_TOKEN و
            # OVERSIGHT_BACKEND_URL در env نباشند، silently skip می‌شود
            # تا setup خراب نشود.
            "claude_runner_auto_enable_new": False,
            # claude_args پیش‌فرض برای workflow های نصب‌شده — هیچ model id
            # ثابتی نه. مدل به‌صورت داینامیک در زمان dispatch توسط backend
            # picker از /v1/models انتخاب می‌شود و به‌عنوان workflow input
            # `claude_model` فرستاده می‌شود. مقدار خالی → build_workflow_yaml
            # پیش‌فرض داینامیک خود را استفاده می‌کند.
            "claude_runner_default_args": "",
            # 🆕 (Auto Backfill AC) — وقتی True، scheduler خودکار backfill
            # AC ها (دکمهٔ زرد) و Phase-3 re-enrich (دکمهٔ بنفش) را با AI
            # اجرا می‌کند و نتیجه در تلگرام می‌آید. کاربر دیگر لازم نیست
            # دستی روی دکمه‌ها بزند. min_hours: فاصلهٔ زمانی بین اجراها
            # (cooldown) تا از مصرف بی‌مورد جلوگیری شود.
            "auto_backfill_ac_enabled": True,
            "auto_backfill_ac_min_hours": 6,
            # last_auto_backfill_ac_at توسط scheduler ست می‌شود (ISO).
            "last_auto_backfill_ac_at": None,
        }

        # 🆕 (Dispatch Storm Prevention) — set از task_id هایی که در حال حاضر
        # یک sync background در حال اجرا برای آنها است. _is_task_dirty
        # تسک‌های inflight را dirty نشمارد تا از dispatch مکرر همان تسک
        # جلوگیری شود. در on_done callback، task_id از set حذف می‌شود.
        # این جلوی snowball effect در mass-regenerate را می‌گیرد.
        self._inflight_sync_tasks: set = set()

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

        # 🔬 (Runtime Verify Stage 1) — normalize AC + task_steps در بارگذاری
        # task های قدیمی AC string دارند → به ساختار {text, verify_method,
        # verify_plan, ...} تبدیل می‌شود. task_steps بدون verify_method ←
        # default static. این normalize **روی state در حافظه** اجرا می‌شود؛
        # ذخیرهٔ مجدد به JSON با اولین _save_tasks اتفاق می‌افتد.
        try:
            from .verify_runtime import normalize_ac_list, normalize_task_steps
        except Exception as _e:
            logger.debug(f"verify_runtime import failed (skipping AC normalize): {_e}")
            normalize_ac_list = None  # type: ignore
            normalize_task_steps = None  # type: ignore

        for t in _read_json(TASKS_FILE, []):
            try:
                # AC + task_steps را قبل از سازندهٔ dataclass normalize کن
                # تا فیلدها از همان ابتدا dict باشند، نه str.
                if normalize_ac_list is not None:
                    try:
                        if "acceptance_criteria" in t:
                            t["acceptance_criteria"] = normalize_ac_list(
                                t.get("acceptance_criteria") or []
                            )
                        if "followup_acceptance_criteria" in t:
                            t["followup_acceptance_criteria"] = normalize_ac_list(
                                t.get("followup_acceptance_criteria") or []
                            )
                    except Exception as _e:
                        logger.debug(f"AC normalize failed for task: {_e}")
                if normalize_task_steps is not None:
                    try:
                        if "task_steps" in t and t.get("task_steps"):
                            t["task_steps"] = normalize_task_steps(t["task_steps"])
                    except Exception as _e:
                        logger.debug(f"task_steps normalize failed: {_e}")
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

    # 🆕 (auto-discover blocklist) — مدیریت لیست repo های حذف‌شده توسط کاربر
    # هدف: auto_discover scheduler دوباره این repos را به watched اضافه نکند
    # مگر کاربر صریحاً add_watched/auto_register_watched بزند.

    def _load_removed_watched(self) -> List[Dict[str, Any]]:
        """خواندن لیست repo های حذف‌شده. ساختار: [{"repo_full_name": "...",
        "removed_at": "ISO"}, ...]"""
        data = _read_json(REMOVED_WATCHED_FILE, {})
        if isinstance(data, dict):
            return list(data.get("items", []) or [])
        # backward-compat: اگر array قدیمی بود
        if isinstance(data, list):
            return data
        return []

    def _save_removed_watched(self, items: List[Dict[str, Any]]) -> None:
        """ذخیره‌ی لیست repo های حذف‌شده."""
        _write_json(REMOVED_WATCHED_FILE, {
            "version": 1,
            "items": items,
        })

    def is_repo_removed_by_user(self, repo_full_name: str) -> bool:
        """آیا این repo قبلاً توسط کاربر از watched حذف شده؟ (case-insensitive)"""
        if not repo_full_name:
            return False
        target = repo_full_name.strip().lower()
        for item in self._load_removed_watched():
            if (item.get("repo_full_name") or "").strip().lower() == target:
                return True
        return False

    def _mark_repo_removed(self, repo_full_name: str, watched_id: str = "") -> None:
        """ثبت repo در لیست removed (هنگام delete_watched).
        اگر قبلاً ثبت شده، فقط timestamp را آپدیت می‌کند."""
        if not repo_full_name:
            return
        target = repo_full_name.strip().lower()
        items = self._load_removed_watched()
        items = [
            it for it in items
            if (it.get("repo_full_name") or "").strip().lower() != target
        ]
        items.append({
            "repo_full_name": repo_full_name.strip(),
            "removed_at": now_iso(),
            "watched_id": watched_id,
        })
        self._save_removed_watched(items)

    def _unmark_repo_removed(self, repo_full_name: str) -> bool:
        """حذف repo از لیست removed (هنگام add_watched/auto_register_watched
        دستی). برمی‌گرداند True اگر چیزی حذف شد."""
        if not repo_full_name:
            return False
        target = repo_full_name.strip().lower()
        items = self._load_removed_watched()
        before = len(items)
        items = [
            it for it in items
            if (it.get("repo_full_name") or "").strip().lower() != target
        ]
        if len(items) < before:
            self._save_removed_watched(items)
            return True
        return False

    def _save_tasks(self, *, skip_sync: bool = False) -> None:
        """ذخیره‌ی atomic لیست تسک‌ها به JSON + dispatch خودکار sync GitHub.

        skip_sync=True: فقط ذخیره. برای callback های داخلی (پس از sync کامل
        شد، فقط می‌خواهیم متادیتای جدید را persist کنیم بدون trigger دوباره).

        skip_sync=False (پیش‌فرض): دیسک نوشته می‌شود + هر تسک "dirty" (که
        از آخرین sync تغییر کرده یا اصلاً sync نشده) به‌صورت fire-and-forget
        به GitHub همگام می‌شود + _index.json پروژه‌های متأثر debounce می‌شود.

        این معماری تضمین می‌کند هر مسیری که _save_tasks() صدا بزند
        (verify دوره‌ای/عمیق/سریع، scan دوره‌ای/موردی/عمیق/سریع، merge،
        consolidation، archive، regenerate، …) همگام‌سازی خودکار اتفاق
        می‌افتد — بدون نیاز به hook دستی در هر نقطه.
        """
        _write_json(TASKS_FILE, [t.to_dict() for t in self.tasks])
        if skip_sync:
            return
        self._sync_dirty_tasks_to_github()

    def _is_task_dirty(self, t: "OversightTask") -> bool:
        """آیا این تسک از آخرین sync تغییر کرده؟ (یا اصلاً sync نشده)

        🆕 اگر تسک در حال حاضر یک sync background در حال اجرا دارد
        (در self._inflight_sync_tasks است)، dirty حساب نمی‌شود تا از
        dispatch مکرر همان تسک جلوگیری شود (dispatch-storm prevention).
        """
        # inflight check اول — حتی اگر synced_at قدیمی است، تا sync جاری
        # تمام نشده re-dispatch نکن
        if getattr(t, "id", None) in self._inflight_sync_tasks:
            return False
        # 🚨 (backend overload fix) — تسک‌های archived که یک بار به فولدر
        # archive/ پوش شده‌اند، نباید با هر updated_at جدید (که verifier
        # housekeeping یا state reconciliation ممکن است ایجاد کند) دوباره
        # push شوند. این کار به‌خصوص پس از bypass streak guard مشکل‌ساز شد:
        # موج archive شد و کل backlog به GitHub flood شد → /health 9s
        # طول می‌کشید → Render shutdown.
        # archive یک‌بار = کافی. اگر نیاز به re-sync archived task داشتیم
        # (مثلاً un-archive)، طرف-call باید github_prompt_synced_at=None
        # یا github_prompt_archived=False ست کند تا dirty بشود.
        if (
            getattr(t, "archived", False)
            and getattr(t, "github_prompt_archived", False)
            and getattr(t, "github_prompt_synced_at", None)
        ):
            return False
        synced = getattr(t, "github_prompt_synced_at", None)
        if not synced:
            return True
        try:
            updated = t.updated_at or ""
            # ISO 8601 UTC strings — مقایسهٔ رشته‌ای ترتیب صحیح می‌دهد
            return updated > synced
        except Exception:
            return True

    def _sync_dirty_tasks_to_github(self) -> None:
        """sync همهٔ تسک‌هایی که از آخرین sync تغییر کرده‌اند.

        - فقط در صورت داشتن GITHUB_TOKEN + running event loop
        - هر پروژه فقط یک rebuild_index debounced می‌گیرد
        - per-repo lock در prompt_github_sync writeهای concurrent را
          سریالیزه می‌کند

        Logging strategy:
        - INFO وقتی dispatch واقعی صورت گرفت (visible در Render logs)
        - DEBUG برای no-op cases (skip ها)
        """
        try:
            from .prompt_github_sync import (
                safe_sync_task, schedule_index_rebuild, compute_execution_priority,
            )
        except Exception as e:
            logger.debug(f"prompt-sync: import failed — skip: {e}")
            return
        token = get_github_token()
        if not token:
            logger.debug("prompt-sync: no GITHUB_TOKEN — skip")
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("prompt-sync: no running loop — skip (sync context)")
            return

        # شناسایی تسک‌های dirty
        dirty: List["OversightTask"] = []
        for t in self.tasks:
            if self._is_task_dirty(t):
                dirty.append(t)
        if not dirty:
            logger.debug("prompt-sync: no dirty tasks — skip")
            return

        # priority را برای dirty ها recompute کن
        for t in dirty:
            try:
                if not getattr(t, "archived", False):
                    t.execution_priority = compute_execution_priority(t)
            except Exception:
                continue

        # 🚨 (backend overload fix) — حداکثر N تسک per save dispatch تا از
        # flood GitHub API و saturate شدن CPU/network روی Render free tier
        # جلوگیری شود. بقیه در save بعدی pickup می‌شوند. priority بالاتر
        # (عدد کمتر) اولویت دارد.
        _MAX_DISPATCH_PER_TICK = 5
        if len(dirty) > _MAX_DISPATCH_PER_TICK:
            dirty.sort(
                key=lambda t: (
                    getattr(t, "execution_priority", 100),
                    getattr(t, "updated_at", "") or "",
                )
            )
            logger.info(
                f"prompt-sync: throttling — {len(dirty)} dirty tasks, "
                f"dispatching top {_MAX_DISPATCH_PER_TICK} this cycle"
            )
            dirty = dirty[:_MAX_DISPATCH_PER_TICK]

        dispatched = 0
        skipped_disabled = 0
        affected_wids: set = set()
        for t in dirty:
            watched = self._find_watched(t.watched_id) if t.watched_id else None
            if watched is None:
                skipped_disabled += 1
                continue
            if not getattr(watched, "prompt_sync_enabled", True):
                skipped_disabled += 1
                continue
            # 🆕 inflight tracking — قبل از dispatch، task_id را در set ثبت کن
            # تا save های بعدی تا تکمیل این sync دوباره dispatch نکنند.
            tid = getattr(t, "id", None)
            if tid:
                self._inflight_sync_tasks.add(tid)

            # closure برای persist + remove از inflight set
            def _make_on_done(task_id: Optional[str]) -> Any:
                def _on_done() -> None:
                    try:
                        _write_json(TASKS_FILE, [tt.to_dict() for tt in self.tasks])
                    except Exception as e:
                        logger.debug(f"prompt-sync persist after sync failed: {e}")
                    finally:
                        if task_id:
                            self._inflight_sync_tasks.discard(task_id)
                return _on_done

            asyncio.create_task(
                safe_sync_task(t, watched, token=token, on_done=_make_on_done(tid))
            )
            dispatched += 1
            affected_wids.add(watched.id)

        # یک rebuild_index debounced برای هر پروژهٔ متأثر
        for wid in affected_wids:
            w = self._find_watched(wid)
            if w is None or not getattr(w, "prompt_sync_enabled", True):
                continue
            schedule_index_rebuild(lambda: list(self.tasks), w, token=token)

        # INFO log: visible در Render تا کاربر بفهمد sync trigger شده
        if dispatched > 0:
            logger.info(
                f"prompt-sync: dispatched {dispatched} task(s) to "
                f"{len(affected_wids)} project(s) "
                f"(skipped: {skipped_disabled} disabled/no-watched)"
            )
        elif skipped_disabled > 0:
            logger.info(
                f"prompt-sync: {skipped_disabled} dirty task(s) found but ALL "
                f"skipped (prompt_sync_enabled=False or watched missing). "
                f"Check PROMPT_SYNC_EXCLUDE_REPOS env var or watched config."
            )

    async def force_sync_and_rebuild_all(
        self, *, watched_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """sync سینکرون همهٔ تسک‌های dirty + rebuild صریح _index.json هر پروژه.

        کاربرد:
          - bootstrap startup (تا مطمئن باشیم _index.json قبل از redeploy ساخته
            می‌شود — بدون اتکا به debounce که در restart از دست می‌رود)
          - /_admin/rebuild-index برای فیکس دستی پروژه‌هایی که _index.json نگرفتند
          - /_admin/backfill برای راه‌اندازی اولیه

        Returns: {"synced": N, "rebuilt": M, "projects": [...]}
        """
        try:
            from .prompt_github_sync import (
                safe_sync_task, rebuild_project_index, compute_execution_priority,
            )
        except Exception as e:
            return {"success": False, "error": f"import_failed: {e}"}

        token = get_github_token()
        if not token:
            return {"success": False, "error": "no_github_token"}

        targets = [
            w for w in self.watched
            if getattr(w, "prompt_sync_enabled", True)
            and (watched_id is None or w.id == watched_id)
        ]
        if not targets:
            return {"success": True, "synced": 0, "rebuilt": 0, "projects": []}

        sem = asyncio.Semaphore(5)
        synced_count = 0
        rebuilt_projects: List[Dict[str, Any]] = []

        def _persist():
            try:
                _write_json(TASKS_FILE, [t.to_dict() for t in self.tasks])
            except Exception as e:
                logger.debug(f"force_sync persist failed: {e}")

        async def _sync_one(t, w):
            async with sem:
                await safe_sync_task(t, w, token=token, on_done=_persist)

        for w in targets:
            project_tasks = [t for t in self.tasks if t.watched_id == w.id]
            # priority recompute برای هر تسک پروژه
            for t in project_tasks:
                try:
                    if not getattr(t, "archived", False):
                        t.execution_priority = compute_execution_priority(t)
                except Exception:
                    pass
            # فقط تسک‌های dirty را sync کن (تسک‌های قبلاً sync شده اسپم نکن)
            dirty_tasks = [t for t in project_tasks if self._is_task_dirty(t)]
            if dirty_tasks:
                await asyncio.gather(
                    *(_sync_one(t, w) for t in dirty_tasks),
                    return_exceptions=True,
                )
                synced_count += len(dirty_tasks)
            # rebuild_index صریح — منتظر اتمام syncها — نه debounce
            try:
                result = await rebuild_project_index(
                    list(self.tasks), w, token=token,
                )
                ok = bool(result.get("success"))
                rebuilt_projects.append({
                    "watched_id": w.id,
                    "repo": w.repo_full_name,
                    "synced_tasks": len(dirty_tasks),
                    "rebuilt_index": ok,
                    "error": result.get("error") if not ok else None,
                })
                if ok:
                    logger.info(
                        f"prompt-sync: rebuilt index for {w.repo_full_name} "
                        f"(synced {len(dirty_tasks)} dirty task(s))"
                    )
                else:
                    logger.warning(
                        f"prompt-sync: rebuild_index failed for "
                        f"{w.repo_full_name}: {result.get('error')}"
                    )
            except Exception as e:
                logger.warning(
                    f"prompt-sync: rebuild_index exception for "
                    f"{w.repo_full_name}: {e}"
                )
                rebuilt_projects.append({
                    "watched_id": w.id,
                    "repo": w.repo_full_name,
                    "synced_tasks": len(dirty_tasks),
                    "rebuilt_index": False,
                    "error": str(e),
                })
        # یک save نهایی برای ذخیرهٔ تمام متادیتای جدید (sha/path/synced_at)
        try:
            _write_json(TASKS_FILE, [t.to_dict() for t in self.tasks])
        except Exception:
            pass
        return {
            "success": True,
            "synced": synced_count,
            "rebuilt": sum(1 for p in rebuilt_projects if p["rebuilt_index"]),
            "projects": rebuilt_projects,
        }

    def _recompute_execution_priorities(
        self, task: Optional["OversightTask"] = None,
    ) -> None:
        """به‌روزرسانی execution_priority.

        اگر task داده شد فقط همان تسک recompute می‌شود (O(1)).
        اگر None باشد، همهٔ تسک‌های غیر-archived (O(N)) — برای startup/backfill.
        """
        try:
            from .prompt_github_sync import compute_execution_priority
        except Exception:
            return
        if task is not None:
            try:
                if not getattr(task, "archived", False):
                    task.execution_priority = compute_execution_priority(task)
            except Exception:
                pass
            return
        for t in self.tasks:
            try:
                if not getattr(t, "archived", False):
                    t.execution_priority = compute_execution_priority(t)
            except Exception:
                continue

    def _schedule_prompt_sync(
        self, task: Optional["OversightTask"] = None, *, rebuild_index: bool = True,
        delete: bool = False,
    ) -> None:
        """fire-and-forget sync یا delete مستقیم برای یک تسک خاص.

        کاربرد: مسیرهایی که _save_tasks() کافی نیست — مثلاً delete_task که
        تسک از self.tasks حذف شده و _save_tasks دیگه نمی‌تونه پیداش کنه.
        برای mutation معمولی (create/update/verify/scan/…) فقط _save_tasks
        صدا بزنید — همگام‌سازی خودکار اتفاق می‌افتد.
        """
        try:
            from .prompt_github_sync import (
                safe_sync_task, safe_delete_task, schedule_index_rebuild,
            )
        except Exception:
            return
        token = get_github_token()
        if not token:
            return

        watched_ids: set = set()

        def _persist_after_sync() -> None:
            """callback ذخیرهٔ متادیتای جدید — بدون trigger مجدد sync."""
            try:
                _write_json(TASKS_FILE, [t.to_dict() for t in self.tasks])
            except Exception as e:
                logger.debug(f"prompt-sync persist after sync failed: {e}")

        per_task_coro = None
        if task is not None:
            watched = self._find_watched(task.watched_id) if task.watched_id else None
            if watched is not None and getattr(watched, "prompt_sync_enabled", True):
                if delete:
                    per_task_coro = safe_delete_task(
                        task, watched, token=token, on_done=_persist_after_sync,
                    )
                else:
                    per_task_coro = safe_sync_task(
                        task, watched, token=token, on_done=_persist_after_sync,
                    )
                watched_ids.add(watched.id)

        # dispatch per-task coro — تنها در صورت داشتن running loop
        if per_task_coro is not None:
            try:
                asyncio.get_running_loop()
                asyncio.create_task(per_task_coro)
            except RuntimeError:
                per_task_coro.close()
                logger.debug("prompt-sync: no running loop; coro closed")

        # rebuild_index با debounce
        if rebuild_index:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return
            target_wids = watched_ids or {
                t.watched_id for t in self.tasks if t.watched_id
            }
            for wid in target_wids:
                w = self._find_watched(wid)
                if w is None or not getattr(w, "prompt_sync_enabled", True):
                    continue
                schedule_index_rebuild(
                    lambda: list(self.tasks),
                    w,
                    token=token,
                )

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
    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """استخراج اولین JSON معتبر از خروجی مدل — با recovery قوی برای
        پاسخ‌های ناقص/truncated/کثیف."""
        if not text:
            return None
        cleaned = text.strip()
        # حذف code fence (```json ... ```)
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        # سعی ۱: parse مستقیم
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # سعی ۲: substring بین اولین `{` و آخرین `}`
        start = cleaned.find("{")
        if start == -1:
            return None
        end = cleaned.rfind("}")
        if end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                pass
        # سعی ۳: recovery قوی — balance brackets + حذف trailing comma + crop
        # تا آخرین فیلد کامل. این برای JSON های truncated شده ضروری است.
        return OversightService._repair_truncated_json(cleaned[start:])

    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
        """تلاش برای ترمیم JSON ناقص:
          1. حذف trailing whitespace
          2. اگر JSON قطع شده داخل string، آن string را ببند
          3. حذف trailing comma
          4. بستن brackets/braces باز
          5. backtrack: اگر هنوز fail، حذف آخرین فیلد ناقص

        برمی‌گرداند dict در صورت موفقیت، None اگر بازیابی ناممکن باشد.
        """
        if not text or not text.startswith("{"):
            return None
        s = text.rstrip()

        # state machine برای پیمایش JSON و شناسایی موقعیت کاربردی
        # شناسایی stack of brackets با احترام به stringها
        def _scan(src: str) -> Dict[str, Any]:
            stack: List[str] = []
            in_str = False
            esc = False
            string_open_idx = -1
            last_complete_value_end = -1  # index بعد از آخرین `,` یا `{` یا کلید-مقدار کامل
            i = 0
            n = len(src)
            while i < n:
                c = src[i]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                else:
                    if c == '"':
                        in_str = True
                        string_open_idx = i
                    elif c in "{[":
                        stack.append("}" if c == "{" else "]")
                    elif c in "}]":
                        if stack and stack[-1] == c:
                            stack.pop()
                            last_complete_value_end = i + 1
                        else:
                            # JSON خراب — بشکن
                            return {
                                "stack": stack,
                                "in_str": in_str,
                                "string_open_idx": string_open_idx,
                                "last_complete_value_end": last_complete_value_end,
                                "broke_at": i,
                            }
                    elif c == "," and not stack:
                        # virgule خارج از همهٔ braces — غیرمنتظره
                        pass
                i += 1
            return {
                "stack": stack,
                "in_str": in_str,
                "string_open_idx": string_open_idx,
                "last_complete_value_end": last_complete_value_end,
                "broke_at": -1,
            }

        state = _scan(s)

        candidate = s
        # اگر در string قطع شده، آن را ببند
        if state["in_str"]:
            candidate = candidate + '"'
        # حذف trailing comma و whitespace
        candidate_r = candidate.rstrip()
        while candidate_r and candidate_r[-1] in ", \t\n":
            candidate_r = candidate_r[:-1]
        candidate = candidate_r

        # بستن brackets/braces باز به ترتیب stack
        for closer in reversed(state["stack"]):
            candidate = candidate + closer

        try:
            return json.loads(candidate)
        except Exception:
            pass

        # اگر هنوز fail، backtrack: از آخرین `,` در سطح روت قطع کن
        # و یک }/] ببند
        # پیدا کردن آخرین `,` در عمق ۱ (بلافاصله داخل root `{`)
        depth = 0
        in_str = False
        esc = False
        last_top_comma = -1
        for i, c in enumerate(s):
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in "{[":
                    depth += 1
                elif c in "}]":
                    depth -= 1
                elif c == "," and depth == 1:
                    last_top_comma = i

        if last_top_comma > 0:
            truncated = s[:last_top_comma] + "}"
            try:
                return json.loads(truncated)
            except Exception:
                pass
            # اگر بازم fail، یک سطح backtrack بیشتر برو
            # یک یا چند bracket باز کن و ببند
            close_attempt = s[:last_top_comma]
            # موقعی که داخل array بودیم
            try:
                # بستن آرایه‌ها و object های باز
                stack: List[str] = []
                in_str2 = False
                esc2 = False
                for c in close_attempt:
                    if in_str2:
                        if esc2:
                            esc2 = False
                        elif c == "\\":
                            esc2 = True
                        elif c == '"':
                            in_str2 = False
                    else:
                        if c == '"':
                            in_str2 = True
                        elif c == "{":
                            stack.append("}")
                        elif c == "[":
                            stack.append("]")
                        elif c in "}]" and stack and stack[-1] == c:
                            stack.pop()
                final = close_attempt
                if in_str2:
                    final += '"'
                for closer in reversed(stack):
                    final += closer
                return json.loads(final)
            except Exception:
                pass

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

        # 🆕 (auto-discover blocklist) — اگر کاربر قبلاً این repo را حذف کرده
        # بود و الان دستی add می‌زند، یعنی نظرش عوض شده. از blocklist حذف کن
        # تا auto-discover هم در آینده آن را تشخیص دهد به‌عنوان valid.
        try:
            if self._unmark_repo_removed(repo):
                logger.info(
                    f"add_watched: repo '{repo}' unmarked from removed list "
                    f"(user re-added manually)"
                )
        except Exception:
            pass

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

        # 🔬 (Runtime Verify auto-detect) — اگر RENDER_API_KEY تنظیم است،
        # سرویس‌های مرتبط با این repo را پیدا کن و URLها را خودکار پر کن.
        # این یک best-effort call است که در background اجرا می‌شود تا
        # add_watched سریع بازگردد.
        try:
            asyncio.create_task(self._autodetect_and_test_runtime(w.id))
        except Exception as _e:
            logger.debug(f"autodetect schedule failed: {_e}")

        # 🤖 (Claude Auto-Runner) — اگر setting سراسری روشن است و env آماده،
        # workflow + secret ها را خودکار روی این ریپوی جدید نصب کن. این
        # best-effort + background است: اگر شکست خورد، watched ساخته
        # می‌ماند و کاربر می‌تواند بعداً دستی روشن کند.
        try:
            if self.settings.get("claude_runner_auto_enable_new", False):
                env = self._claude_runner_env()
                if all(env.values()):
                    asyncio.create_task(self.enable_claude_runner(w.id))
                    logger.info(
                        f"add_watched: claude_runner auto-enable scheduled for {w.id}"
                    )
                else:
                    missing = [k for k, v in env.items() if not v]
                    logger.info(
                        f"add_watched: claude_runner auto-enable skipped — "
                        f"env_missing={missing}"
                    )
        except Exception as _e:
            logger.warning(f"claude_runner auto-enable failed: {_e}")
        return w.to_dict()

    async def autodetect_runtime_for_all_watched(self) -> Dict[str, Any]:
        """🔬 backfill — برای همهٔ watched هایی که هنوز URL ندارند یا
        test-result ندارند، autodetect + test را اجرا می‌کند.

        برای lifespan startup ایده‌آل است.
        """
        ids_to_run: List[str] = []
        for w in self.watched:
            needs_detect = not w.frontend_base_url and not w.backend_base_url
            needs_test = (
                (w.frontend_base_url or w.backend_base_url)
                and not w.runtime_connection_test
            )
            if needs_detect or needs_test:
                ids_to_run.append(w.id)
        for wid in ids_to_run:
            try:
                await self._autodetect_and_test_runtime(wid)
            except Exception as e:
                logger.debug(f"backfill {wid} failed: {e}")
        return {"processed": len(ids_to_run), "watched_count": len(self.watched)}

    async def _autodetect_and_test_runtime(self, watched_id: str) -> None:
        """🔬 background task — auto-detect frontend/backend URLs از Render
        + اجرای تست اتصال + ذخیرهٔ نتیجه."""
        try:
            w = next((x for x in self.watched if x.id == watched_id), None)
            if w is None:
                return
            # 1) auto-detect URLs
            from .verify_runtime.render_autodetect import (
                detect_render_urls_for_repo, detect_repo_url,
            )
            detected = await detect_render_urls_for_repo(w.repo_full_name)
            changed = False
            if detected.get("frontend_base_url") and not w.frontend_base_url:
                w.frontend_base_url = detected["frontend_base_url"]
                changed = True
            if detected.get("backend_base_url") and not w.backend_base_url:
                w.backend_base_url = detected["backend_base_url"]
                changed = True
            # repo_url is fine — clone URL از قبل ثبت شده. در آینده اگر کاربر
            # repo را clone کرد و local path اضافه کند، runtime_repo_path پر می‌شود.
            if changed:
                w.runtime_autodetected = True
                w.updated_at = now_iso()
                async with self._lock:
                    self._save_watched()
                logger.info(
                    f"autodetect watched {watched_id}: "
                    f"frontend={w.frontend_base_url}, backend={w.backend_base_url}"
                )

            # 2) تست اتصال (اگر حداقل یک URL داریم)
            if w.frontend_base_url or w.backend_base_url:
                test_result = await self._test_runtime_connection_inner(w)
                w.runtime_connection_test = test_result
                w.updated_at = now_iso()
                async with self._lock:
                    self._save_watched()
        except Exception as e:
            logger.warning(f"autodetect_and_test_runtime {watched_id} failed: {e}")

    async def _test_runtime_connection_inner(self, w: "WatchedProject") -> Dict[str, Any]:
        """تست GET به base URLs و برگرداندن نتیجه با timestamp."""
        import httpx
        out: Dict[str, Any] = {"at": now_iso()}
        for label, url in (
            ("frontend", w.frontend_base_url),
            ("backend", w.backend_base_url),
        ):
            if not url:
                out[label] = {"ok": False, "error": "URL تنظیم نشده"}
                continue
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
                    r = await c.get(url)
                out[label] = {
                    "ok": 200 <= r.status_code < 500,
                    "status": r.status_code,
                    "url": url,
                }
            except Exception as e:
                out[label] = {"ok": False, "error": str(e)[:200], "url": url}
        return out

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

        # 🆕 (auto-discover blocklist) — اگر این فراخوانی از مسیر دستی است
        # (Creator یا github_import)، repo را از blocklist حذف کن.
        # مسیر auto_discover_scheduler خودش قبل از این فراخوانی blocklist
        # را چک می‌کند و اگر در آن باشد، اصلاً auto_register_watched را
        # صدا نمی‌زند. پس اینجا فقط برای مسیرهای دستی مهم است.
        if source != "auto_discover_scheduler":
            try:
                if self._unmark_repo_removed(repo):
                    logger.info(
                        f"auto_register_watched: repo '{repo}' unmarked from "
                        f"removed list (source={source})"
                    )
            except Exception:
                pass

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

        # 🔬 (Runtime Verify auto-detect) — همان منطق add_watched
        try:
            asyncio.create_task(self._autodetect_and_test_runtime(w.id))
        except Exception as _e:
            logger.debug(f"autodetect schedule (auto_register) failed: {_e}")

        # 🤖 (Claude Auto-Runner) — همان منطق add_watched
        try:
            if self.settings.get("claude_runner_auto_enable_new", False):
                env = self._claude_runner_env()
                if all(env.values()):
                    asyncio.create_task(self.enable_claude_runner(w.id))
                    logger.info(
                        f"auto_register_watched: claude_runner auto-enable "
                        f"scheduled for {w.id} (source={source})"
                    )
        except Exception as _e:
            logger.warning(f"claude_runner auto-enable (auto_register) failed: {_e}")

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
                        # 🆕 (Phase 4) — حالت verify
                        "verify_mode",
                        # 🆕 (Phase 5) — Scan V5 flags
                        "stale_detection_enabled",
                        "delta_analysis_enabled",
                        "runtime_discovery_enabled",
                        "outcome_data_enabled",
                        "logic_audit_enabled",
                        "notification_audit_enabled",
                        "inspector_session_enabled",
                        "auto_task_checklist_mode",
                        "cleanup_tasks_enabled",
                        "auto_task_notify_sound",
                        "scan_notify_sound",
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
                        # 🆕 (Smart Task Lifecycle) Dedup + Quality Audit
                        "auto_regenerate_old_prompts",
                        "prompt_quality_threshold",
                        "dedup_in_manual_create",
                        "dedup_score_threshold",
                        # 🔬 (Runtime Verify Stage 4) — UI/API probe config
                        "frontend_base_url",
                        "backend_base_url",
                        "runtime_auth",
                        "runtime_repo_path",
                        "runtime_autodetected",
                        "runtime_connection_test",
                    }
                    for k, v in updates.items():
                        if k in allowed:
                            # 🆕 (Phase 4) — normalize verify_mode به deep/fast
                            if k == "verify_mode":
                                v = str(v or "deep").strip().lower()
                                if v not in ("deep", "fast"):
                                    v = "deep"
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
        # 🤖 (Claude Auto-Runner) — اگر workflow نصب شده، **پیش از حذف
        # watched** از ریپوی هدف uninstall کن. این کار خارج از lock انجام
        # می‌شود (شامل HTTP) و اگر شکست خورد، حذف watched ادامه می‌یابد —
        # کاربر می‌تواند بعداً دستی فایل را پاک کند.
        try:
            pre = next((w for w in self.watched if w.id == watched_id), None)
            if pre and getattr(pre, "claude_runner_enabled", False):
                _r = await self.disable_claude_runner(watched_id)
                if not _r.get("success"):
                    logger.warning(
                        f"delete_watched: claude_runner uninstall errors: "
                        f"{_r.get('errors')}"
                    )
        except Exception as _e:
            logger.warning(
                f"delete_watched: claude_runner uninstall raised: {_e}"
            )

        async with self._lock:
            # 🆕 قبل از حذف، repo_full_name را پیدا کن تا blocklist را آپدیت کنیم
            target = next((w for w in self.watched if w.id == watched_id), None)
            target_repo = target.repo_full_name if target else ""

            before = len(self.watched)
            self.watched = [w for w in self.watched if w.id != watched_id]
            removed = len(self.watched) < before
            if removed:
                self._save_watched()
                # 🆕 (auto-discover blocklist) — ثبت در لیست removed تا
                # scheduler دوباره این repo را auto-add نکند. اگر کاربر دستی
                # add_watched/auto_register_watched بزند، از لیست removed
                # حذف می‌شود (user wants it back).
                if target_repo:
                    try:
                        self._mark_repo_removed(target_repo, watched_id=watched_id)
                        logger.info(
                            f"delete_watched: repo '{target_repo}' marked as "
                            f"removed (auto-discover will skip it)"
                        )
                    except Exception as e:
                        logger.warning(f"failed to mark repo as removed: {e}")
            return removed

    def _find_watched(self, watched_id: str) -> Optional[WatchedProject]:
        for w in self.watched:
            if w.id == watched_id:
                return w
        return None

    # ====================================================================
    # 🆕 (Claude Auto-Runner) — enable/disable/status
    # ====================================================================

    def _claude_runner_env(self) -> Dict[str, str]:
        """خواندن secret ها و config از env سرور.

        برای جلوگیری از log کردن مقادیر، فقط presence/absence را برمی‌گرداند.
        مقادیر واقعی فقط در زمان install/uninstall به sub-service پاس می‌شوند.
        """
        return {
            "oauth_token": (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or "").strip(),
            "external_token": (os.environ.get("EXTERNAL_TOOL_TOKEN") or "").strip(),
            "backend_url": (os.environ.get("OVERSIGHT_BACKEND_URL") or "").strip(),
        }

    async def enable_claude_runner(
        self, watched_id: str, *, claude_args: Optional[str] = None,
    ) -> Dict[str, Any]:
        """نصب workflow Claude Auto-Runner روی یک پروژهٔ watched.

        پیش‌نیازهای env: CLAUDE_CODE_OAUTH_TOKEN, EXTERNAL_TOOL_TOKEN,
        OVERSIGHT_BACKEND_URL باید ست شده باشند. در غیر این صورت با خطای
        قابل‌فهم برمی‌گردد و چیزی روی ریپو ست نمی‌کند.
        """
        watched = self._find_watched(watched_id)
        if watched is None:
            return {"success": False, "error": "watched_not_found"}
        env = self._claude_runner_env()
        missing = [k for k, v in env.items() if not v]
        if missing:
            return {
                "success": False,
                "error": "env_missing",
                "missing": missing,
                "hint": (
                    "روی سرور Render این env varها را ست کنید: "
                    "CLAUDE_CODE_OAUTH_TOKEN, EXTERNAL_TOOL_TOKEN, "
                    "OVERSIGHT_BACKEND_URL"
                ),
            }
        gh_token = get_github_token()
        if not gh_token:
            return {"success": False, "error": "no_github_token"}

        from .claude_runner_bootstrap import install_runner, WORKFLOW_PATH

        # claude_args=None or "" → install_runner از template داینامیک
        # YAML استفاده می‌کند (--model ${{ inputs.claude_model || 'sonnet' }})
        # که هیچ model id ثابتی هاردکد نمی‌کند. اگر کاربر/تنظیمات explicit
        # claude_args داده، آن را پاس بده.
        args = claude_args or self.settings.get("claude_runner_default_args") or None
        result = await install_runner(
            watched,
            gh_token=gh_token,
            oauth_token=env["oauth_token"],
            external_token=env["external_token"],
            backend_url=env["backend_url"],
            claude_args=args,
        )
        async with self._lock:
            watched.claude_runner_enabled = bool(result.get("success"))
            watched.claude_runner_workflow_path = WORKFLOW_PATH if result.get("success") else None
            watched.claude_runner_installed_at = (
                now_iso() if result.get("success") else watched.claude_runner_installed_at
            )
            if result.get("success"):
                watched.claude_runner_last_error = None
            else:
                watched.claude_runner_last_error = "; ".join(result.get("errors") or []) or "unknown"
            self._save_watched()
        # 🆕 Telegram feedback: نصب runner — تأیید فوری برای کاربر
        try:
            from .notification_service import notification_service
            ok = bool(result.get("success"))
            errs = result.get("errors") or []
            if ok:
                msg = (
                    f"🤖 *Claude Auto-Runner فعال شد*\n\n"
                    f"📁 `{watched.repo_full_name}`\n"
                    f"📂 workflow: `{WORKFLOW_PATH}`\n\n"
                    f"از این پس هر تسکی که به این پروژه اضافه شود، خودکار "
                    f"توسط Claude Code (headless) اجرا و مستقیماً به main "
                    f"commit و push می‌شود."
                )
            else:
                msg = (
                    f"⚠️ *نصب Claude Auto-Runner ناموفق*\n\n"
                    f"📁 `{watched.repo_full_name}`\n"
                    f"🔍 خطاها:\n" + "\n".join(f"  • {e}" for e in errs[:5])
                )
            asyncio.create_task(notification_service.notify_event(
                "claude_runner_enable_attempt",
                msg,
                subject="Claude Runner",
                priority="low",
                project_name=watched.repo_full_name,
                watched_id=watched.id,
            ))
        except Exception as _e:
            logger.debug(f"enable_claude_runner notification skipped: {_e}")
        return {
            "success": bool(result.get("success")),
            "errors": result.get("errors", []),
            "watched": watched.to_dict(),
        }

    async def disable_claude_runner(self, watched_id: str) -> Dict[str, Any]:
        """حذف workflow + secret ها از ریپو + خاموش کردن flag در state."""
        watched = self._find_watched(watched_id)
        if watched is None:
            return {"success": False, "error": "watched_not_found"}
        gh_token = get_github_token()
        if not gh_token:
            return {"success": False, "error": "no_github_token"}

        from .claude_runner_bootstrap import uninstall_runner

        result = await uninstall_runner(watched, gh_token=gh_token)
        async with self._lock:
            watched.claude_runner_enabled = False
            watched.claude_runner_workflow_path = None
            watched.claude_runner_last_error = (
                None if result.get("success") else "; ".join(result.get("errors") or [])
            )
            self._save_watched()
        # 🆕 Telegram feedback: غیرفعال‌سازی runner
        try:
            from .notification_service import notification_service
            asyncio.create_task(notification_service.notify_event(
                "claude_runner_disabled",
                f"🤖⏸ *Claude Auto-Runner غیرفعال شد*\n\n"
                f"📁 `{watched.repo_full_name}`\n"
                f"workflow و secret ها از ریپو حذف شدند. تسک‌های جدید "
                f"همچنان به prompt/ push می‌شوند ولی خودکار اجرا نخواهند شد.",
                subject="Claude Runner",
                priority="low",
                project_name=watched.repo_full_name,
                watched_id=watched.id,
            ))
        except Exception as _e:
            logger.debug(f"disable_claude_runner notification skipped: {_e}")
        return {
            "success": bool(result.get("success")),
            "errors": result.get("errors", []),
            "watched": watched.to_dict(),
        }

    # ------------------------------------------------------------------
    # 🔒 (verify-after-complete lock) — تمرکز روی تسک در حال verify
    # ------------------------------------------------------------------
    # وقتی Claude /complete می‌زند، تسک وارد فاز verify می‌شود. تا تمام
    # شدن verify، هیچ workflow_dispatch دیگر برای همان watched trigger
    # نمی‌شود. این lock تضمین می‌کند تغییرات فولدر prompt/ (تسک جدید،
    # حذف، sync) باعث انحراف تمرکز از این تسک نشود.

    VERIFY_LOCK_STALE_MINUTES: int = 30

    def _acquire_verify_lock(self, watched_id: str, task_id: str) -> bool:
        """قفل کردن watched روی task مشخص. caller باید _save_watched() بزند.

        Returns True اگر lock گرفته شد (بدون رقیب). False اگر watched
        قبلاً روی تسک دیگری lock شده (نباید overwrite کنیم).
        """
        watched = self._find_watched(watched_id)
        if watched is None:
            return False
        existing = getattr(watched, "claude_runner_verifying_task_id", None)
        if existing and existing != task_id:
            # اگر stale است، آزادش کن
            started = getattr(watched, "claude_runner_verifying_started_at", None)
            if not self._is_verify_lock_stale(started):
                logger.warning(
                    f"_acquire_verify_lock: watched {watched_id} already locked "
                    f"on task {existing}, cannot acquire for {task_id}"
                )
                return False
            logger.info(
                f"_acquire_verify_lock: stale lock on {watched_id} cleared "
                f"(was task {existing}, started {started})"
            )
        watched.claude_runner_verifying_task_id = task_id
        watched.claude_runner_verifying_started_at = now_iso()
        return True

    def _release_verify_lock(self, watched_id: str) -> None:
        """آزاد کردن lock. caller باید _save_watched() بزند."""
        watched = self._find_watched(watched_id)
        if watched is None:
            return
        watched.claude_runner_verifying_task_id = None
        watched.claude_runner_verifying_started_at = None

    @classmethod
    def _is_verify_lock_stale(cls, started_at: Optional[str]) -> bool:
        """آیا lock بیش از VERIFY_LOCK_STALE_MINUTES دقیقه است؟"""
        if not started_at:
            return True
        try:
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            ts = _dt.fromisoformat(started_at.replace("Z", "+00:00"))
            return (_dt.now(_tz.utc) - ts) > _td(minutes=cls.VERIFY_LOCK_STALE_MINUTES)
        except Exception:
            return True  # parse fail → consider stale (safer)

    def is_watched_verify_locked(self, watched_id: str) -> bool:
        """آیا این watched الان در فاز verify-after-complete است؟

        خودش stale check را انجام می‌دهد. اگر stale بود، lock را پاک
        می‌کند و False برمی‌گرداند.
        """
        watched = self._find_watched(watched_id)
        if watched is None:
            return False
        task_id = getattr(watched, "claude_runner_verifying_task_id", None)
        if not task_id:
            return False
        started = getattr(watched, "claude_runner_verifying_started_at", None)
        if self._is_verify_lock_stale(started):
            logger.info(
                f"is_watched_verify_locked: stale lock cleared for {watched_id} "
                f"(task {task_id}, started {started})"
            )
            watched.claude_runner_verifying_task_id = None
            watched.claude_runner_verifying_started_at = None
            try:
                self._save_watched()
            except Exception:
                pass
            return False
        return True

    # ====================================================================
    # 🆕 (External Pending Verify Sweeper) — recovery برای تسک‌هایی که
    # /complete رسیده ولی verify-after-complete اجرا نشده.
    # ====================================================================

    # تسک‌ها که verification_status=applied_externally_pending_verify اند
    # و حداقل این مقدار از mark زمان گذشته باشد، تازه پردازش می‌شوند.
    # این فاصله به verify-after-complete اصلی فرصت می‌دهد start بزند.
    EXTERNAL_VERIFY_SWEEP_GRACE_SECONDS: int = 120  # 2 دقیقه
    # حداکثر تسک در هر تیک — جلوگیری از overload
    EXTERNAL_VERIFY_SWEEP_MAX_PER_TICK: int = 2
    # اگر lock بیش از این مدت قدیمی است، فرض می‌کنیم verify در پس‌زمینه
    # کشته شده (مثلاً Render instance reboot). آزاد + retry می‌کنیم.
    EXTERNAL_VERIFY_FORCE_RELEASE_MINUTES: int = 15

    async def _sweep_pending_external_verifies(self) -> None:
        """پیدا کردن تسک‌های applied_externally_pending_verify و trigger
        مجدد _verify_then_chain روی آنها — اگر verify-after-complete زنده
        نمانده باشد.

        قواعد:
        - فقط تسک‌های مرتبط با watched که claude_runner_workflow_path دارند
        - حداقل 2 دقیقه از manually_marked_applied_at گذشته باشد
        - حداکثر 2 تسک در هر تیک
        - اگر verify-lock روی watched فعال است:
          * اگر <15 دقیقه: skip (در حال اجراست)
          * اگر >=15 دقیقه: assume killed، force release، retry
        """
        from datetime import datetime, timezone, timedelta

        # late import — جلوگیری از circular
        try:
            from ..api.routes.external_prompts import _verify_then_chain
        except Exception as _e:
            logger.debug(f"sweeper: cannot import _verify_then_chain: {_e}")
            return

        now = datetime.now(timezone.utc)
        grace = timedelta(seconds=self.EXTERNAL_VERIFY_SWEEP_GRACE_SECONDS)
        force_release = timedelta(minutes=self.EXTERNAL_VERIFY_FORCE_RELEASE_MINUTES)

        # کاندیدها
        candidates: List[Tuple[Any, Any]] = []
        for t in self.tasks:
            if t.verification_status != "applied_externally_pending_verify":
                continue
            if getattr(t, "archived", False):
                continue
            if not getattr(t, "watched_id", None):
                continue
            watched = self._find_watched(t.watched_id)
            if watched is None:
                continue
            if not getattr(watched, "claude_runner_workflow_path", None):
                continue
            # mark time check
            mark = getattr(t, "manually_marked_applied_at", None) or t.updated_at
            if not mark:
                continue
            try:
                mark_dt = datetime.fromisoformat(mark.replace("Z", "+00:00"))
            except Exception:
                continue
            if (now - mark_dt) < grace:
                continue  # خیلی تازه — verify-after-complete اصلی فرصت داشته باشد
            candidates.append((t, watched))

        if not candidates:
            return

        # اولویت: قدیمی‌تر اول
        candidates.sort(key=lambda pr: pr[0].updated_at or "")

        processed = 0
        spawned: List[str] = []
        for t, watched in candidates:
            if processed >= self.EXTERNAL_VERIFY_SWEEP_MAX_PER_TICK:
                break
            # وضعیت lock روی watched
            cur_lock_task = getattr(watched, "claude_runner_verifying_task_id", None)
            cur_lock_started = getattr(watched, "claude_runner_verifying_started_at", None)
            lock_age_ok = True  # یعنی lock زیر آستانهٔ force_release است (احتمالاً زنده)
            if cur_lock_task and cur_lock_started:
                try:
                    s_dt = datetime.fromisoformat(cur_lock_started.replace("Z", "+00:00"))
                    lock_age_ok = (now - s_dt) < force_release
                except Exception:
                    lock_age_ok = False  # نتوانستیم parse کنیم — کهنه فرض می‌کنیم

            if cur_lock_task:
                if cur_lock_task != t.id:
                    # یک تسک دیگر در حال verify است — صبر می‌کنیم
                    continue
                # lock روی همین تسک
                if lock_age_ok:
                    # کم سن — احتمالاً verify-after-complete اصلی هنوز در حال
                    # اجراست. صبر می‌کنیم تا یا تمام شود یا به آستانه برسد.
                    continue
                # کهنه — assume verify در پس‌زمینه کشته شده. آزاد و retry می‌کنیم.
                logger.warning(
                    f"sweeper: force-releasing stale verify-lock on watched={watched.id} "
                    f"task={t.id} (started {cur_lock_started}, age >= "
                    f"{self.EXTERNAL_VERIFY_FORCE_RELEASE_MINUTES} min)"
                )
                async with self._lock:
                    self._release_verify_lock(watched.id)
                    self._save_watched()

            # acquire lock + spawn (now lock is either None or on same task & released)
            async with self._lock:
                if not self._acquire_verify_lock(watched.id, t.id):
                    continue
                self._save_watched()

            logger.info(
                f"sweeper: triggering verify-then-chain for task={t.id} "
                f"watched={watched.id} (recovery — no lock or stale lock cleared)"
            )
            asyncio.create_task(
                _verify_then_chain(
                    task_id=t.id,
                    watched_id=watched.id,
                    agent_id="claude-runner-sweeper",
                )
            )
            spawned.append(t.id)
            processed += 1

        if spawned:
            logger.info(
                f"sweeper: spawned verify-then-chain for {len(spawned)} pending "
                f"external verifies: {spawned}"
            )

    async def repair_claude_runner_permissions(
        self, watched_id: str,
    ) -> Dict[str, Any]:
        """دوباره تنظیمات لازم را روی GitHub repo اعمال می‌کند بدون reinstall.

        برای وقتی کار می‌کند که workflow نصب است ولی run ها در Queued
        گیر می‌کنند (معمولاً به‌دلیل Workflow permissions روی Read-only).

        کارهایی که انجام می‌دهد:
        1. PUT actions/permissions/workflow → Read and write
        2. اعتبار GitHub token را چک می‌کند

        برمی‌گرداند: {success, permissions_result, hints}
        """
        watched = self._find_watched(watched_id)
        if watched is None:
            return {"success": False, "error": "watched_not_found"}
        if not getattr(watched, "claude_runner_workflow_path", None):
            return {
                "success": False,
                "error": "workflow_not_installed",
                "hint": "ابتدا runner را نصب کنید (دکمهٔ اجرا با Claude روی یک تسک یا توگل 🤖 watched)",
            }
        gh_token = get_github_token()
        if not gh_token:
            return {"success": False, "error": "no_github_token"}
        from .claude_runner_bootstrap import set_workflow_permissions_write
        from .prompt_github_sync import _resolve_repo_and_branch

        resolved = _resolve_repo_and_branch(watched)
        if not resolved:
            return {"success": False, "error": "repo_not_resolvable"}
        owner, repo, _branch = resolved
        perm_res = await set_workflow_permissions_write(
            owner, repo, gh_token=gh_token,
        )
        hints: List[str] = []
        if not perm_res.get("success"):
            hints.append(
                "set_workflow_permissions_write خطا داد. احتمالاً GitHub PAT "
                "اجازهٔ admin روی repo را ندارد. در GitHub repo settings → "
                "Actions → General → 'Workflow permissions' را دستی روی "
                "'Read and write permissions' بگذارید."
            )
        else:
            hints.append(
                "تنظیمات اعمال شد. run های Queued باید ظرف ۱-۲ دقیقه شروع "
                "شوند. اگر هنوز گیر بود، در GitHub UI run را cancel کنید و "
                "از دکمهٔ '🤖 اجرا با Claude' دوباره trigger بزنید."
            )
        return {
            "success": bool(perm_res.get("success")),
            "permissions_result": perm_res,
            "hints": hints,
        }

    def get_claude_runner_status(self, watched_id: str) -> Dict[str, Any]:
        """گزارش وضعیت Claude Runner برای یک watched (بدون call به GitHub)."""
        watched = self._find_watched(watched_id)
        if watched is None:
            return {"success": False, "error": "watched_not_found"}
        env = self._claude_runner_env()
        return {
            "success": True,
            "enabled": bool(watched.claude_runner_enabled),
            "installed_at": watched.claude_runner_installed_at,
            "workflow_path": watched.claude_runner_workflow_path,
            "last_error": watched.claude_runner_last_error,
            "env_ready": all(env.values()),
            "env_missing": [k for k, v in env.items() if not v],
        }

    async def list_claude_runner_runs(
        self, watched_id: str, *, limit: int = 10,
    ) -> Dict[str, Any]:
        """فهرست اجراهای اخیر workflow این پروژه (proxy به GitHub Actions API).

        نتیجه برای نمایش در پنل «اجراهای خودکار اخیر» استفاده می‌شود.
        کاربر روی هر run می‌تواند کلیک کند و مستقیماً به صفحه Actions
        گیت‌هاب برود.
        """
        watched = self._find_watched(watched_id)
        if watched is None:
            return {"success": False, "error": "watched_not_found"}
        gh_token = get_github_token()
        if not gh_token:
            return {"success": False, "error": "no_github_token"}
        from .claude_runner_bootstrap import list_workflow_runs
        return await list_workflow_runs(
            watched, gh_token=gh_token, limit=limit,
        )

    # ====================================================================
    # 🆕 (Manual Single-Task Trigger) — اجرای دستی یک تسک خاص توسط
    # Claude Auto-Runner، مستقل از auto-runner پروژه. کاربر می‌تواند بدون
    # روشن کردن claude_runner_enabled، فقط همین یک تسک را اجرا کند.
    # workflow YAML باید قبلاً نصب شده باشد (claude_runner_workflow_path ست).
    # ====================================================================

    async def install_claude_runner_manual_only(
        self, watched_id: str, *, claude_args: Optional[str] = None,
    ) -> Dict[str, Any]:
        """نصب workflow YAML بدون فعال‌سازی auto-trigger on push.

        تفاوت با enable_claude_runner:
        - YAML + secret ها نصب می‌شوند (مثل enable)
        - `claude_runner_enabled` همچنان False باقی می‌ماند (مثل پیش‌فرض)
        - یعنی push تسک‌های جدید به prompt/ هیچ workflow ای را trigger نمی‌کند
        - فقط manual trigger (force=True) کار می‌کند

        برای موقعی است که کاربر می‌خواهد یک تسک خاص را با Claude اجرا کند
        ولی نمی‌خواهد همهٔ تسک‌های پروژه خودکار اجرا شوند.
        """
        watched = self._find_watched(watched_id)
        if watched is None:
            return {"success": False, "error": "watched_not_found"}
        env = self._claude_runner_env()
        missing = [k for k, v in env.items() if not v]
        if missing:
            return {
                "success": False,
                "error": "env_missing",
                "missing": missing,
                "hint": (
                    "روی سرور Render این env varها را ست کنید: "
                    "CLAUDE_CODE_OAUTH_TOKEN, EXTERNAL_TOOL_TOKEN, "
                    "OVERSIGHT_BACKEND_URL"
                ),
            }
        gh_token = get_github_token()
        if not gh_token:
            return {"success": False, "error": "no_github_token"}

        from .claude_runner_bootstrap import install_runner, WORKFLOW_PATH

        # claude_args=None or "" → install_runner از template داینامیک
        # YAML استفاده می‌کند (--model ${{ inputs.claude_model || 'sonnet' }})
        # که هیچ model id ثابتی هاردکد نمی‌کند. اگر کاربر/تنظیمات explicit
        # claude_args داده، آن را پاس بده.
        args = claude_args or self.settings.get("claude_runner_default_args") or None
        result = await install_runner(
            watched,
            gh_token=gh_token,
            oauth_token=env["oauth_token"],
            external_token=env["external_token"],
            backend_url=env["backend_url"],
            claude_args=args,
        )
        async with self._lock:
            # ⚠️ مهم: claude_runner_enabled را تغییر نمی‌دهیم. اگر کاربر
            # قبلاً enable کرده بود، همان طور True می‌ماند. اگر False بود
            # (پیش‌فرض)، False می‌ماند — یعنی auto-trigger on push خاموش.
            watched.claude_runner_workflow_path = WORKFLOW_PATH if result.get("success") else None
            watched.claude_runner_installed_at = (
                now_iso() if result.get("success") else watched.claude_runner_installed_at
            )
            if result.get("success"):
                watched.claude_runner_last_error = None
            else:
                watched.claude_runner_last_error = "; ".join(result.get("errors") or []) or "unknown"
            self._save_watched()
        return {
            "success": bool(result.get("success")),
            "errors": result.get("errors", []),
            "mode": "manual_only",
            "watched": watched.to_dict(),
        }

    async def run_single_task_via_claude(
        self,
        task_id: str,
        *,
        agent_id: str = "claude-manual-trigger",
        lease_minutes: int = 30,  # legacy unused (workflow self-claims with default lease)
    ) -> Dict[str, Any]:
        """trigger دستی Claude Auto-Runner برای یک تسک خاص.

        - workflow YAML باید قبلاً در repo نصب شده باشد (با enable_claude_runner)
        - claude_runner_enabled لازم نیست True باشد (force trigger)
        - تسک **pre-claim نمی‌شود** — workflow وقتی شروع شد خودش با
          agent_id='claude-code-action' (طبق MASTER_PROMPT) /claim می‌زند.
          pre-claim با agent_id دیگر باعث 409 در /claim واقعی workflow می‌شود.
        - فقط workflow_dispatch با target_task_id فرستاده می‌شود تا Claude
          همان task_id را اجرا کند به‌جای /next.
        - اگر یک تسک دیگر در حال verify است (verify-lock فعال)، rejection
          از trigger_workflow_dispatch برمی‌گردد (skipped + reason).
        - اگر تسک هم‌اکنون توسط agent دیگری در حال اجراست و lease فعال، باز
          هم workflow را trigger می‌کنیم — GitHub queue آن را behind صف می‌گذارد
          (concurrency group) و وقتی نوبت رسید، اگر هنوز locked است، Claude
          /claim خواهد گرفت 409 و exit می‌کند. این از race بدون pre-claim
          محافظت می‌کند.
        - agent_id داده‌شده فقط برای logging/notification استفاده می‌شود.

        Returns:
          {"success": bool, "task_id": str, "dispatch_result": dict, "error"?: str}
        """
        from .claude_runner_bootstrap import trigger_workflow_dispatch

        # validation سبک تحت قفل (بدون mutation)
        async with self._lock:
            t = next((x for x in self.tasks if x.id == task_id), None)
            if t is None:
                return {"success": False, "error": "task_not_found"}
            if getattr(t, "archived", False):
                return {"success": False, "error": "task_archived"}
            if not getattr(t, "watched_id", None):
                return {"success": False, "error": "task_has_no_watched_project"}
            # وضعیت تسک باید pickable باشد (pending یا awaiting_review). اگر
            # تسک قبلاً done/failed/running است، workflow /claim می‌کند 409 و
            # هیچ کاری نمی‌شود — بهتر است در همین لایه نگه داریم.
            from .prompt_github_sync import PICKABLE_STATUSES as _PICKABLE
            if t.status not in _PICKABLE:
                return {
                    "success": False,
                    "error": "task_not_pickable",
                    "task_status": t.status,
                    "hint": (
                        f"وضعیت تسک «{t.status}» قابل اجرا نیست. "
                        f"فقط تسک‌های pending یا awaiting_review قابل trigger هستند."
                    ),
                }
            watched = self._find_watched(t.watched_id)
            if watched is None:
                return {"success": False, "error": "watched_not_found"}

        # 🆕 (Auto-install manual-only) — اگر workflow هنوز نصب نیست، آن را
        # در حالت manual-only نصب کن (workflow_path ست می‌شود، enabled همچنان
        # False می‌ماند). این یعنی auto-trigger on push روشن نمی‌شود — کاربر
        # باید explicitly از panel "اجرای خودکار" را روشن کند اگر بخواهد.
        auto_installed: bool = False
        install_error: Optional[Dict[str, Any]] = None
        if not getattr(watched, "claude_runner_workflow_path", None):
            install_res = await self.install_claude_runner_manual_only(watched.id)
            if not install_res.get("success"):
                # نصب شکست خورد — خطای install را به caller پاس بده
                install_error = install_res
            else:
                auto_installed = True
                # workflow_path تازه در DB ست شد ولی reference local باید refresh شود
                watched = self._find_watched(t.watched_id)  # type: ignore[assignment]

        if install_error is not None:
            err = install_error.get("error", "install_failed")
            return {
                "success": False,
                "error": "workflow_install_failed",
                "install_error": err,
                "install_detail": install_error,
                "hint": install_error.get("hint")
                or "نصب workflow Claude Runner روی پروژه شکست خورد",
            }

        gh_token = get_github_token()
        if not gh_token:
            return {"success": False, "error": "no_github_token"}

        # trigger workflow با target_task_id — force=True تا قید
        # claude_runner_enabled bypass شود (فقط workflow_path لازم است)
        # 🆕 retry برای 404 transient (workflow_not_indexed_yet): اگر workflow
        # تازه نصب شده، GitHub چند ثانیه طول می‌کشد تا index کند. با backoff
        # تا ۴ بار تلاش می‌کنیم (مجموع ~۲۰ ثانیه) برای اولین trigger بعد
        # auto-install. برای dispatch روی workflow از قبل موجود، فقط یک تلاش.
        max_attempts = 4 if auto_installed else 1
        delays = [3.0, 5.0, 8.0]
        dispatch_result: Dict[str, Any] = {}
        # 🤖 (dynamic model) — قبل از trigger، آخرین مدل tier درست را برای
        # این تسک خاص از /v1/models بگیر و به workflow بفرست. اگر None
        # برگشت (مثلاً OAuth token ندارد)، workflow از default خودش
        # (alias `sonnet`) استفاده می‌کند که Claude Code CLI به آخرین
        # Sonnet route می‌کند.
        from .claude_runner_bootstrap import pick_model_for_task
        # 🆕 (centralization — stage 3) — این مسیر دکمهٔ «اجرا از طریق
        # کلاد» تک‌تسک است. consumer_key="claude_single_task" تا اگر
        # کاربر در صفحهٔ مدل‌ها این consumer را خاموش کرده باشد، Cloud
        # Code انتخاب نشود و workflow از default خودش استفاده کند.
        _picked_model = await pick_model_for_task(
            t, consumer_key="claude_single_task",
        )
        for attempt in range(max_attempts):
            dispatch_result = await trigger_workflow_dispatch(
                watched,
                gh_token=gh_token,
                target_task_id=task_id,
                force=True,
                claude_model=_picked_model,
            )
            # موفقیت یا خطای غیر-transient → بیرون
            if dispatch_result.get("success") or not dispatch_result.get("transient"):
                break
            # transient (workflow_not_indexed_yet) → صبر و retry
            if attempt < max_attempts - 1:
                wait = delays[min(attempt, len(delays) - 1)]
                logger.info(
                    f"run_single_task_via_claude: workflow not indexed yet for "
                    f"{watched.repo_full_name}, retry #{attempt + 1} in {wait}s"
                )
                await asyncio.sleep(wait)

        # skipped (مثلاً verify_in_progress) یعنی trigger واقعاً ارسال نشد
        # — برای caller باید مثل خطا رفتار کند
        dispatch_success = bool(dispatch_result.get("success")) and not dispatch_result.get("skipped")
        out: Dict[str, Any] = {
            "success": dispatch_success,
            "task_id": task_id,
            "watched_id": watched.id,
            "repo": watched.repo_full_name,
            "dispatch_result": dispatch_result,
            "agent_id": agent_id,
        }
        # علامت‌گذاری اگر runner تازه auto-install شد (manual-only mode)
        if auto_installed:
            out["auto_installed"] = True
            out["install_mode"] = "manual_only"
        # سرفصل وقتی YAML قدیمی است و auto-retry بدون inputs موفق شد —
        # کاربر باید بداند که target_task_id اعمال نشد
        if dispatch_result.get("outdated_workflow"):
            out["outdated_workflow"] = True
            out["warning"] = dispatch_result.get("warning") or (
                "workflow YAML قدیمی است؛ runner را غیرفعال و دوباره نصب کنید."
            )
        return out

    # ====================================================================
    # 🆕 (Reference Projects) — profile + normalization + validation
    # ====================================================================

    def _build_current_project_profile(
        self, watched_id: Optional[str],
    ) -> str:
        """ساخت یک خلاصهٔ کوتاه از پروژهٔ فعلی برای fusion text.

        AI با این متن می‌تواند تفاوت‌های stack/dependency/نام‌گذاری پروژهٔ
        فعلی با مراجع را تشخیص دهد و توصیه‌ها را تطبیق دهد (نه کپی کور).

        خروجی Markdown است (یا "" اگر watched_id داده نشده/پیدا نشد).
        """
        if not watched_id:
            return ""
        watched = self._find_watched(watched_id)
        if watched is None:
            return ""
        lines: List[str] = []
        lines.append(f"- **Repo**: `{watched.repo_full_name}`")
        if watched.language:
            lines.append(f"- **زبان غالب**: {watched.language}")
        if watched.default_branch and watched.default_branch != "main":
            lines.append(f"- **branch پیش‌فرض**: `{watched.default_branch}`")
        if watched.tags:
            lines.append(f"- **برچسب‌ها**: {', '.join(watched.tags[:8])}")
        if watched.user_notes and watched.user_notes.strip():
            notes = watched.user_notes.strip()[:600]
            lines.append(f"- **یادداشت کاربر دربارهٔ این پروژه**: {notes}")
        # تلاش برای استخراج stack از last_scan_inventory (اگر موجود)
        try:
            inv = watched.last_scan_inventory or {}
            stacks = inv.get("detected_stacks") or inv.get("tech_stack") or []
            if isinstance(stacks, list) and stacks:
                lines.append(f"- **Stack شناسایی‌شده**: {', '.join(map(str, stacks[:10]))}")
            frameworks = inv.get("frameworks") or []
            if isinstance(frameworks, list) and frameworks:
                lines.append(f"- **Frameworkها**: {', '.join(map(str, frameworks[:10]))}")
        except Exception:
            pass
        if not lines:
            return ""
        return "\n".join(lines)

    def _normalize_selected_projects(
        self,
        items: Any,
        *,
        exclude_watched_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """نرمال‌سازی + اعتبارسنجی لیست پروژه‌های مرجع.

        هر آیتم باید قابل تطبیق با یکی از پروژه‌های watched باشد —
        شناسایی از طریق `project_id` (watched.id) یا `project_path`
        (repo_full_name) انجام می‌شود. آیتم‌های نامعتبر silently drop می‌شوند.

        خروجی: لیست تمیز با ساختار:
            {project_id, project_path, is_selected}
        فقط مواردی که `is_selected=True` هستند نگه داشته می‌شوند.

        `exclude_watched_id` — اگر داده شود، خود پروژهٔ تسک از لیست مرجع
        حذف می‌شود (نمی‌توان پروژه را مرجع خودش قرار داد).
        """
        if not items or not isinstance(items, list):
            return []
        # نقشهٔ سریع watched ها (هم بر اساس id و هم repo_full_name)
        by_id: Dict[str, WatchedProject] = {w.id: w for w in self.watched}
        by_path: Dict[str, WatchedProject] = {
            (w.repo_full_name or "").strip().lower(): w
            for w in self.watched
            if w.repo_full_name
        }
        seen: set = set()
        result: List[Dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            is_selected = bool(raw.get("is_selected", True))
            if not is_selected:
                continue
            pid = (raw.get("project_id") or "").strip()
            ppath = (raw.get("project_path") or "").strip()
            target: Optional[WatchedProject] = None
            if pid and pid in by_id:
                target = by_id[pid]
            elif ppath:
                target = by_path.get(ppath.lower())
            if target is None:
                logger.debug(
                    f"_normalize_selected_projects: drop unknown item "
                    f"(id={pid!r}, path={ppath!r})"
                )
                continue
            if exclude_watched_id and target.id == exclude_watched_id:
                logger.debug(
                    f"_normalize_selected_projects: drop self-reference "
                    f"({target.id})"
                )
                continue
            key = target.id
            if key in seen:
                continue
            seen.add(key)
            # 🆕 (focus_notes) — متن focus کاربر برای این پروژهٔ مرجع را حفظ کن
            # (اگر داده شده). cap به 500 کاراکتر تا overflow نشود.
            focus = str(raw.get("focus_notes") or "").strip()[:500]
            result.append({
                "project_id": target.id,
                "project_path": target.repo_full_name,
                "is_selected": True,
                "focus_notes": focus,
            })
        return result

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

    # ================================================================
    # 🆕 (Smart Task Lifecycle) Similarity detection
    # ================================================================

    @staticmethod
    def _normalize_text(s: str) -> str:
        """نرمال‌سازی متن برای similarity — حذف stopwords + lowercase + punctuation."""
        import re as _re
        s = (s or "").strip().lower()
        for stop in [
            "the", "a", "an", "is", "are", "to", "of", "for", "in", "on", "with",
            "and", "or", "but",
            "و", "در", "از", "به", "که", "یک", "این", "آن", "را", "با", "هم",
            "بر", "تا", "می", "های", "ها", "اما", "یا",
        ]:
            s = _re.sub(rf"\b{stop}\b", " ", s)
        s = _re.sub(r"[^\w\s؀-ۿ]", " ", s)
        s = _re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def _jaccard(cls, a: str, b: str) -> float:
        na, nb = cls._normalize_text(a), cls._normalize_text(b)
        if not na or not nb:
            return 0.0
        if na == nb:
            return 1.0
        sa, sb = set(na.split()), set(nb.split())
        if not sa or not sb:
            return 0.0
        inter = len(sa & sb)
        union = len(sa | sb)
        return inter / union if union else 0.0

    @classmethod
    def _ngram_overlap(cls, a: str, b: str, n: int = 3) -> float:
        """Token n-gram overlap — برای متن‌های بلندتر مثل raw_idea دقیق‌تر از Jaccard ساده."""
        na, nb = cls._normalize_text(a), cls._normalize_text(b)
        if not na or not nb:
            return 0.0
        ta = na.split()
        tb = nb.split()
        if len(ta) < n or len(tb) < n:
            # برای متن‌های خیلی کوتاه به Jaccard ساده fallback
            return cls._jaccard(a, b)
        ga = {" ".join(ta[i:i + n]) for i in range(len(ta) - n + 1)}
        gb = {" ".join(tb[i:i + n]) for i in range(len(tb) - n + 1)}
        if not ga or not gb:
            return 0.0
        inter = len(ga & gb)
        union = len(ga | gb)
        return inter / union if union else 0.0

    @staticmethod
    def _ac_text(ac: Any) -> str:
        """🔬 (Runtime Verify Stage 1) — متن AC را برمی‌گرداند، خواه str قدیمی
        خواه dict جدید با فیلد text."""
        if isinstance(ac, dict):
            return str(ac.get("text") or "").strip()
        return str(ac).strip() if ac is not None else ""

    @classmethod
    def _ac_overlap(
        cls, a: Optional[List[Any]], b: Optional[List[Any]]
    ) -> float:
        """تطابق acceptance_criteria — هر AC با هم Jaccard بزرگ‌تر از 0.6 یعنی match.
        ورودی می‌تواند str یا dict (ساختار جدید) باشد.
        """
        la_texts = [cls._ac_text(x) for x in (a or [])]
        lb_texts = [cls._ac_text(x) for x in (b or [])]
        la = [x for x in la_texts if x]
        lb = [x for x in lb_texts if x]
        if not la or not lb:
            return 0.0
        matched = 0
        for x in la:
            for y in lb:
                if cls._jaccard(x, y) >= 0.6:
                    matched += 1
                    break
        total = max(len(la), len(lb))
        return matched / total if total else 0.0

    def find_similar_active_tasks(
        self,
        project_id: Optional[str],
        candidate_title: str,
        candidate_raw_idea: str = "",
        candidate_acceptance_criteria: Optional[List[str]] = None,
        *,
        jaccard_threshold: float = 0.75,
        raw_idea_overlap_threshold: float = 0.6,
        score_threshold: float = 0.65,
        include_archived: bool = False,
        include_done: bool = False,
        limit: int = 5,
    ) -> List[SimilarityMatch]:
        """کاندیدهای مشابه را در tasks موجود (همان watched/project) با امتیاز
        وزن‌دار بازمی‌گرداند.

        وزن‌ها:
          - title_jaccard: 40%
          - idea_overlap (3-gram): 40%
          - ac_overlap: 20%

        آستانه‌های راهنما (هر کدام می‌توانند به‌تنهایی trigger شوند):
          - title_jaccard >= jaccard_threshold (0.75) → کاندید قوی
          - idea_overlap >= raw_idea_overlap_threshold (0.6) → کاندید قوی
          - score کلی >= score_threshold (0.65) → کاندید نهایی
        """
        candidate_title = (candidate_title or "").strip()
        if not candidate_title and not candidate_raw_idea:
            return []
        cand_ac = candidate_acceptance_criteria or []

        # کاندیدها: همان watched_id، active (نه archived/done/cancelled)
        candidates: List[OversightTask] = []
        for t in self.tasks:
            if project_id is not None and t.watched_id != project_id:
                continue
            if not include_archived and getattr(t, "archived", False):
                continue
            if not include_done:
                if t.status in ("done", "cancelled"):
                    continue
                if t.verification_status == "done":
                    continue
            candidates.append(t)

        matches: List[SimilarityMatch] = []
        for t in candidates:
            tj = self._jaccard(candidate_title, t.title or "")
            io = self._ngram_overlap(
                candidate_raw_idea or candidate_title,
                t.raw_idea or t.title or "",
            )
            ao = self._ac_overlap(cand_ac, t.acceptance_criteria)

            score = (tj * 0.4) + (io * 0.4) + (ao * 0.2)
            reasons: List[str] = []
            if tj >= jaccard_threshold:
                reasons.append(f"title Jaccard {tj:.2f}")
            if io >= raw_idea_overlap_threshold:
                reasons.append(f"raw_idea overlap {io:.2f}")
            if ao >= 0.5:
                reasons.append(f"AC overlap {ao:.2f}")

            # یک کاندید فقط در صورتی برگردانده می‌شود که حداقل یکی از
            # آستانه‌های نام/ایده برآورده شود، یا score کلی >= threshold
            qualifies = (
                tj >= jaccard_threshold
                or io >= raw_idea_overlap_threshold
                or score >= score_threshold
            )
            if not qualifies:
                continue

            matches.append(
                SimilarityMatch(
                    task_id=t.id,
                    title=t.title or "",
                    score=round(score, 4),
                    title_jaccard=round(tj, 4),
                    idea_overlap=round(io, 4),
                    ac_overlap=round(ao, 4),
                    reasons=reasons,
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    async def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        from .oversight_strong_prompt import extract_target_files, extract_acceptance_criteria
        from .verify_runtime import normalize_ac_list, normalize_task_steps

        watched_id = payload.get("watched_id")
        watched = self._find_watched(watched_id) if watched_id else None
        if watched_id and not watched:
            raise ValueError("پروژه تحت نظارت یافت نشد")

        title = payload.get("title", "").strip() or "تسک بدون عنوان"
        prompt = payload.get("prompt", "").strip()
        # 🆕 defensive disclaimer prepend — هر مسیری که create_task را صدا می‌زند
        # (API مستقیم، scan، consolidation، inspector، ...) تضمین می‌کند که
        # EXECUTOR_DISCLAIMER (شامل بخش وابستگی‌ها و همگام‌سازی) در ابتدای
        # prompt باشد. اگر prompt قبلاً از idea_to_prompt آمده، header در 500
        # کاراکتر اول هست و prepend skip می‌شود.
        if prompt:
            try:
                from .oversight_strong_prompt import EXECUTOR_DISCLAIMER
                if "یادداشت مهم برای مدل اجراکننده" not in prompt[:500]:
                    prompt = EXECUTOR_DISCLAIMER + "\n" + prompt
            except Exception as _e:
                logger.debug(f"create_task: disclaimer prepend skipped: {_e}")
        # 🆕 (C5 — بند ۹) — title validator + retry. اگر AI عنوان generic داد،
        # یک پاس دیگر با hint قوی‌تر می‌زنیم تا عنوان معنادار شود.
        if title != "تسک بدون عنوان" and not self._validate_title_quality(title):
            try:
                _better = await self._generate_better_title(
                    idea=(payload.get("raw_idea") or "")[:2000],
                    prompt=prompt[:3000],
                    fallback=title,
                    model_id=payload.get("model_id"),
                )
                if _better and _better != title:
                    logger.info(
                        f"create_task: title improved from '{title}' → '{_better}'"
                    )
                    title = _better
            except Exception as _te:
                logger.debug(f"create_task: title regenerate skipped: {_te}")
        if not prompt:
            raise ValueError("prompt خالی است")

        raw_idea = (payload.get("raw_idea") or "").strip()
        force_create = bool(payload.get("force_create"))
        merge_into_task_id = payload.get("merge_into_task_id")
        source = payload.get("source") or "user"

        # استخراج target_files و acceptance_criteria از پرامپت در صورت نبودن
        target_files = payload.get("target_files") or extract_target_files(prompt)
        # 🔬 (Runtime Verify Stage 1) — AC را به ساختار استاندارد تبدیل کن.
        # کاربر می‌تواند str قدیمی، dict جدید، یا ترکیبی پاس کند —
        # normalize_ac_list هر سه را به ساختار {text, verify_method, verify_plan,
        # evidence_history} تبدیل می‌کند. اگر هیچ AC ای نبود، از پرامپت extract می‌شود.
        raw_ac = payload.get("acceptance_criteria") or extract_acceptance_criteria(prompt)
        acceptance_criteria = normalize_ac_list(raw_ac)
        # 🔬 (Runtime Verify Stage 2) — AC ها را با AI enrich کن تا verify_method
        # و verify_plan ساختاریافته بگیرند. این یک best-effort call است — اگر
        # شکست بخورد، AC ها با method=static باقی می‌مانند.
        # فقط برای task هایی که تازه ساخته می‌شوند (نه merge/duplicate) لازم
        # است، چون یکبار است و سرعت ایجاد را کم می‌کند.
        try:
            from .verify_runtime import enrich_acs_with_verify_plans
            acceptance_criteria = await enrich_acs_with_verify_plans(
                acceptance_criteria,
                title=title,
                description=raw_idea or prompt[:500],
                target_files=target_files,
                model_id=(payload.get("model_id") or None),
            )
        except Exception as _e:
            logger.debug(f"AC enrich at create_task skipped: {_e}")

        execution_mode = payload.get("execution_mode")
        if not execution_mode:
            execution_mode = (watched.default_execution_mode if watched else "manual") or "manual"

        # ───────────── 🆕 (Smart Task Lifecycle) Dedup Gate ─────────────
        # 1) اگر merge_into_task_id داده شده → مستقیماً merge بزن (mode 3)
        if merge_into_task_id:
            try:
                from .task_merge_service import get_task_merge_service
                merge_service = get_task_merge_service()
                merged_task = await merge_service.apply_merge_simple(
                    existing_task_id=merge_into_task_id,
                    candidate_title=title,
                    candidate_raw_idea=raw_idea,
                    candidate_prompt=prompt,
                    candidate_acceptance_criteria=acceptance_criteria,
                    candidate_target_files=target_files,
                    source=source,
                )
                if merged_task is None:
                    raise ValueError("تسک هدف برای ادغام یافت نشد")
                return CreateTaskResult(
                    status="merged",
                    task=merged_task,
                    similar_matches=[],
                    merge_preview=None,
                    message=f"با تسک «{merged_task.get('title', '')[:60]}» ادغام شد.",
                ).to_dict()
            except Exception as e:
                logger.warning(f"create_task: merge_into failed: {e}")
                # شکست در merge → بدون duplicate detection ایجاد کن (پیش‌فرض ایمن)
                force_create = True

        # 2) اگر force_create نیست و dedup فعال است → بررسی مشابهت
        dedup_enabled = (
            not force_create
            and (watched is None or getattr(watched, "dedup_in_manual_create", True))
        )
        if dedup_enabled and watched_id:
            try:
                threshold = float(
                    getattr(watched, "dedup_score_threshold", 0.65) if watched else 0.65
                )
            except Exception:
                threshold = 0.65
            matches = self.find_similar_active_tasks(
                project_id=watched_id,
                candidate_title=title,
                candidate_raw_idea=raw_idea or title,
                candidate_acceptance_criteria=acceptance_criteria,
                score_threshold=threshold,
            )
            if matches:
                # تسک ایجاد نمی‌شود — duplicate_detected برگشت داده می‌شود
                # رویداد notify از سمت route یا frontend صدا می‌شود (نه اینجا، تا
                # await در پاسخ HTTP بلاک نشود).
                try:
                    asyncio.create_task(
                        self._notify_duplicate_detected(
                            watched=watched,
                            candidate_title=title,
                            matches=matches,
                            source=source,
                        )
                    )
                except Exception:
                    pass
                return CreateTaskResult(
                    status="duplicate_detected",
                    task=None,
                    similar_matches=[m.to_dict() for m in matches],
                    merge_preview=None,
                    message=(
                        f"{len(matches)} تسک مشابه پیدا شد. "
                        f"می‌توانید ادغام کنید یا با force_create=true ایجاد جداگانه بسازید."
                    ),
                ).to_dict()
        # ─────────────────────────────────────────────────────────────────

        # 🔔 (Reminder feature) — اگر type==reminder، reminder_at لازم است و
        # reminder_state اولیه = "scheduled". اگر type!=reminder، این فیلدها
        # پاک می‌مانند (default).
        _type = payload.get("type", "other")
        _is_reminder = (_type or "").lower().strip() == "reminder"
        _reminder_at = payload.get("reminder_at") if _is_reminder else None
        _reminder_state = "scheduled" if (_is_reminder and _reminder_at) else "none"
        _reminder_repeat_rule = (
            payload.get("reminder_repeat_rule") if _is_reminder else None
        )

        t = OversightTask(
            id=str(uuid.uuid4()),
            watched_id=watched_id,
            project_full_name=watched.repo_full_name if watched else payload.get("project_full_name", ""),
            title=title,
            prompt=prompt,
            raw_idea=raw_idea,
            type=_type,
            priority=payload.get("priority", "medium"),
            status=payload.get("status", "pending"),
            deadline=payload.get("deadline"),
            source=source,
            execution_mode=execution_mode,
            target_files=target_files,
            acceptance_criteria=acceptance_criteria,
            reminder_at=_reminder_at,
            reminder_state=_reminder_state,
            reminder_repeat_rule=_reminder_repeat_rule,
        )
        # 🆕 (Reference Projects) — اعتبارسنجی + ذخیره selected_projects.
        # آیتم‌های نامعتبر drop می‌شوند (سکوت)، خود پروژه از لیست مرجع
        # حذف می‌شود تا self-reference نباشد.
        _sel = self._normalize_selected_projects(
            payload.get("selected_projects"),
            exclude_watched_id=watched_id,
        )
        if _sel:
            t.selected_projects = _sel
        # اگر reminder، یک رکورد scheduled در history ثبت کن
        if _is_reminder and _reminder_at:
            t.reminder_history.append({
                "ts": now_iso(),
                "action": "scheduled",
                "at": _reminder_at,
            })
        # 🆕 (Multi-pass Checklist) — اگر idea_to_prompt مراحل تولید کرده، آن‌ها را
        # به تسک متصل کن. هر مرحله شامل id/title/scope و وضعیت اولیه pending است.
        incoming_steps = payload.get("task_steps") or []
        if isinstance(incoming_steps, list) and incoming_steps:
            normalized_steps: List[Dict[str, Any]] = []
            for s in incoming_steps:
                if not isinstance(s, dict):
                    continue
                normalized_steps.append({
                    "id": s.get("id") or (len(normalized_steps) + 1),
                    "title": (s.get("title") or "").strip() or f"مرحله {len(normalized_steps) + 1}",
                    "scope": (s.get("scope") or "").strip(),
                    "raw_excerpt": s.get("raw_excerpt", ""),
                    "key_terms": s.get("key_terms") or [],
                    "status": s.get("status") or "pending",
                    "completion_pct": int(s.get("completion_pct") or 0),
                    "remaining": s.get("remaining", ""),
                    "evidence": s.get("evidence", ""),
                    "last_verified_at": s.get("last_verified_at"),
                    "completed_at": s.get("completed_at"),
                    # 🔬 (Runtime Verify Stage 1) — اگر idea_to_prompt مرحله را
                    # با verify_method/plan داد، حفظ کن (Stage 2 آن را پر می‌کند).
                    "verify_method": s.get("verify_method"),
                    "verify_plan": s.get("verify_plan"),
                })
            if normalized_steps:
                # 🔬 normalize نهایی برای پرکردن default های verify_method/plan
                # روی step هایی که AI آن‌ها را نگفت.
                t.task_steps = normalize_task_steps(normalized_steps)
                t.overall_completion_pct = int(payload.get("overall_completion_pct") or 0)
        async with self._lock:
            self.tasks.append(t)
            self._save_tasks()

        # 🆕 (Stage 7 — File Attachment) — اگر sessionهای آپلود همراه payload
        # داده شده، آن‌ها را به این task ربط بده تا verify/extraction بعدی
        # بتواند به متن استخراج‌شده دسترسی داشته باشد. این outside lock است
        # چون UploadSessionService خودش lock مستقل دارد.
        # 🛡 (audit fix) — اگر attach fail کرد، با retry و سپس notification
        # روی task هشدار می‌گذاریم تا کاربر متوجه شود attachments پیوست
        # نشدند.
        attached_sids = payload.get("upload_session_ids") or []
        if isinstance(attached_sids, list) and attached_sids:
            attach_ok = False
            try:
                from .oversight_upload_session import get_upload_session_service
                upload_svc = get_upload_session_service()
                n = await upload_svc.attach_to_task(attached_sids, t.id)
                attach_ok = n > 0
            except Exception as e:
                logger.warning(f"create_task: attach upload sessions failed: {e}")
            if not attach_ok:
                # علامت‌گذاری روی task — کاربر در UI می‌بیند که فایل‌ها وصل نشدند
                logger.warning(
                    f"create_task {t.id}: attach_to_task returned 0 — هیچ session "
                    f"به این تسک ربط نخورد. کاربر باید دستی attach کند."
                )
        # 🆕 (Prompt-GitHub Sync) — همگام‌سازی خودکار از داخل _save_tasks
        # هندل می‌شود؛ اینجا hook دستی لازم نیست.
        return CreateTaskResult(
            status="created",
            task=t.to_dict(),
            similar_matches=[],
            merge_preview=None,
            message="تسک ساخته شد.",
        ).to_dict()

    async def _notify_duplicate_detected(
        self,
        *,
        watched: Optional[WatchedProject],
        candidate_title: str,
        matches: List[SimilarityMatch],
        source: str,
    ) -> None:
        """ارسال notification غیر-blocking برای duplicate_detected (best-effort)."""
        try:
            from .notification_service import notification_service
            project_name = watched.repo_full_name if watched else ""
            lines = [
                "🔍 *تسک‌های مشابه پیدا شد*",
                f"📁 پروژه: `{project_name}`",
                f"📥 منبع: `{source}`",
                f"✏️ ورودی: _{candidate_title[:100]}_",
                "",
                f"🔁 {len(matches)} مورد مشابه:",
            ]
            for i, m in enumerate(matches[:3], 1):
                lines.append(f"  {i}. «{m.title[:60]}» — شباهت {int(m.score * 100)}٪")
            await notification_service.notify_event(
                "task_duplicate_detected",
                "\n".join(lines),
                subject="تسک مشابه پیدا شد",
                priority="low",
                project_name=project_name,
                watched_id=watched.id if watched else None,
            )
        except Exception as e:
            logger.debug(f"_notify_duplicate_detected failed: {e}")

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
                        # 🆕 (C5) — pin + title management
                        "pinned",
                        "manual_title_override",
                        "tags",
                        # 🆕 (Reference Projects)
                        "selected_projects",
                    }
                    # 🆕 (C5) — اگر title از updates آمد، title_history را به‌روز کن
                    _old_title = t.title
                    _title_changed = False
                    for k, v in updates.items():
                        if k in allowed:
                            # 🆕 (Reference Projects) — قبل از set،
                            # selected_projects را اعتبارسنجی + نرمال کن.
                            if k == "selected_projects":
                                v = self._normalize_selected_projects(
                                    v, exclude_watched_id=t.watched_id,
                                )
                            setattr(t, k, v)
                            # وقتی archived true شد، archived_at را ست کن
                            if k == "archived" and v:
                                t.archived_at = now_iso()
                            elif k == "archived" and not v:
                                t.archived_at = None
                            # وقتی pinned true شد، pinned_at ست شود
                            if k == "pinned" and v:
                                t.pinned_at = now_iso()
                            elif k == "pinned" and not v:
                                t.pinned_at = None
                            # تشخیص تغییر title برای history
                            if k == "title" and v and v != _old_title:
                                _title_changed = True
                    # 🆕 (C5) — اگر title از طریق این endpoint تغییر کرد:
                    # 1) entry در title_history (source=manual پیش‌فرض) via _record_title_change
                    # 2) اگر کاربر صریحاً manual_title_override نفرستاد، آن را True کن
                    #    (یعنی این یک manual edit است، AI نباید بعداً override کند)
                    if _title_changed:
                        _src = str(updates.get("_title_change_source") or "manual")
                        self._record_title_change(t, _old_title, t.title, _src)
                        if "manual_title_override" not in updates and _src == "manual":
                            t.manual_title_override = True
                    # اگر prompt تغییر کرده، target_files و AC را هم به‌روز کن
                    if "prompt" in updates and updates["prompt"]:
                        if not updates.get("target_files"):
                            t.target_files = extract_target_files(t.prompt)
                        if not updates.get("acceptance_criteria"):
                            t.acceptance_criteria = extract_acceptance_criteria(t.prompt)
                    t.updated_at = now_iso()
                    self._save_tasks()
                    # 🆕 (Prompt-GitHub Sync) — همگام‌سازی خودکار توسط _save_tasks
                    return t.to_dict()
        return None

    async def delete_task(self, task_id: str) -> bool:
        async with self._lock:
            target = next((t for t in self.tasks if t.id == task_id), None)
            before = len(self.tasks)
            self.tasks = [t for t in self.tasks if t.id != task_id]
            removed = len(self.tasks) < before
            if removed:
                self._save_tasks()
                # 🆕 (Prompt-GitHub Sync) — حذف فایل از ریپو + بازسازی index
                if target is not None:
                    self._schedule_prompt_sync(target, rebuild_index=True, delete=True)
            return removed

    # ================================================================
    # 🆕 (Smart Task Lifecycle) Prompt quality scoring
    # ================================================================

    @staticmethod
    def _score_prompt_quality(task: "OversightTask") -> int:
        """امتیاز کیفیت پرامپت (0..100). ۰ = خالی/خراب، ۱۰۰ = پروژهٔ ایده‌آل.

        معیارها (پیش‌گزیدهٔ heuristic، بدون AI):
          - پرامپت موجود است + حداقل ۲۰۰ کاراکتر (base 30)
          - حضور هدف/مأموریت یا «##» (header markdown)
          - حضور EXECUTOR_DISCLAIMER
          - حضور acceptance_criteria
          - حضور target_files
          - عدم truncation (پایان ناقص)
        """
        prompt = (task.prompt or "").strip()
        if not prompt:
            return 5
        # spec: پرامپت < 200 کاراکتر = صراحتاً کیفیت پایین (max 10)
        if len(prompt) < 200:
            return 10
        score = 30
        # length tier (200..∞)
        score += 10  # base bonus for >=200
        if len(prompt) >= 800:
            score += 10
        if len(prompt) >= 2000:
            score += 5
        # structure
        if "##" in prompt or "###" in prompt:
            score += 10
        # DISCLAIMER
        if "یادداشت مهم برای مدل اجراکننده" in prompt[:1500]:
            score += 10
        # acceptance criteria
        if task.acceptance_criteria and len(task.acceptance_criteria) >= 2:
            score += 10
        elif task.acceptance_criteria:
            score += 5
        # target files
        if task.target_files:
            score += 5
        # standard sections (ُفارسی + انگلیسی)
        for kw in [
            "هدف", "Goal", "context", "Context", "تست", "Test",
            "Acceptance", "معیار",
        ]:
            if kw in prompt:
                score += 1
        score = min(score, 100)
        # truncation penalty
        last_chars = prompt[-20:].strip()
        if last_chars.endswith("...") or last_chars.endswith("…"):
            score = max(score - 25, 5)
        # ناقص بودن backticks یا code fences
        if prompt.count("```") % 2 != 0:
            score = max(score - 10, 5)
        return max(0, min(score, 100))

    async def audit_prompt_quality(self, watched_id: Optional[str] = None) -> Dict[str, Any]:
        """تمام تسک‌های active را برای کیفیت پرامپت scan می‌کند و امتیاز ست می‌کند.

        خروجی: شمارش‌ها + لیست low_quality_task_ids.
        """
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        scanned = 0
        low_quality: List[str] = []
        threshold_default = 60
        async with self._lock:
            for t in self.tasks:
                if watched_id is not None and t.watched_id != watched_id:
                    continue
                if getattr(t, "archived", False):
                    continue
                if t.status in ("done", "cancelled"):
                    continue
                if t.verification_status == "done":
                    continue
                scanned += 1
                q = self._score_prompt_quality(t)
                t.prompt_quality_score = q
                t.last_quality_audit_at = ts
                # threshold از watched اگر موجود
                w = self._find_watched(t.watched_id) if t.watched_id else None
                thr = int(
                    getattr(w, "prompt_quality_threshold", threshold_default)
                    if w else threshold_default
                )
                if q < thr:
                    low_quality.append(t.id)
            self._save_tasks()
            # last_prompt_audit_at روی watched
            if watched_id:
                w = self._find_watched(watched_id)
                if w:
                    w.last_prompt_audit_at = ts
                    self._save_watched()
        return {
            "scanned": scanned,
            "low_quality_count": len(low_quality),
            "low_quality_task_ids": low_quality,
        }

    async def regenerate_low_quality_prompts(
        self,
        watched_id: Optional[str] = None,
        *,
        max_count: int = 5,
        reason: str = "manual_override",
    ) -> Dict[str, Any]:
        """پرامپت تسک‌های با کیفیت پایین را بازتولید می‌کند.

        - ابتدا audit_prompt_quality صدا زده می‌شود (تا امتیازها به‌روز شوند).
        - حداکثر max_count تسک بازتولید می‌شود (rate-limit برای هزینهٔ AI).
        - تسک‌ها به ترتیب صعودی امتیاز sort می‌شوند (بدترین اول).
        """
        audit = await self.audit_prompt_quality(watched_id)
        ids = list(audit.get("low_quality_task_ids", []))
        # sort: بدترین کیفیت اول
        ids_with_score: List[tuple] = []
        for tid in ids:
            t = next((x for x in self.tasks if x.id == tid), None)
            if t:
                ids_with_score.append((tid, t.prompt_quality_score or 0))
        ids_with_score.sort(key=lambda x: x[1])
        ids_to_run = [tid for tid, _ in ids_with_score[:max_count]]

        regenerated: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        for tid in ids_to_run:
            try:
                t_before = next((x for x in self.tasks if x.id == tid), None)
                old_quality = t_before.prompt_quality_score if t_before else 0
                res = await self.regenerate_prompt_for_task(tid)
                if res is None:
                    failed.append({"task_id": tid, "error": "not_found"})
                    continue
                # امتیاز جدید
                t_after = next((x for x in self.tasks if x.id == tid), None)
                new_quality = self._score_prompt_quality(t_after) if t_after else 0
                if t_after:
                    t_after.prompt_quality_score = new_quality
                regenerated.append({
                    "task_id": tid,
                    "title": (res.get("title") or "")[:120],
                    "old_quality": old_quality,
                    "new_quality": new_quality,
                })
                # notify (best-effort)
                try:
                    from .notification_service import notification_service
                    await notification_service.notify_event(
                        "prompt_regenerated",
                        (
                            "🔄 *پرامپت بازتولید شد*\n"
                            f"📌 تسک: «{(res.get('title') or '')[:80]}»\n"
                            f"📊 کیفیت: {old_quality}٪ → {new_quality}٪\n"
                            f"📥 دلیل: `{reason}`"
                        ),
                        subject="پرامپت بازتولید شد",
                        priority="low",
                        project_name=res.get("project_full_name") or "",
                        watched_id=res.get("watched_id"),
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"regenerate_low_quality: {tid} failed: {e}")
                failed.append({"task_id": tid, "error": str(e)[:200]})
        async with self._lock:
            self._save_tasks()
        return {
            "scanned": audit.get("scanned", 0),
            "low_quality_count": audit.get("low_quality_count", 0),
            "regenerated": regenerated,
            "regenerated_count": len(regenerated),
            "failed": failed,
            "skipped": max(0, len(ids) - len(ids_to_run)),
            "max_count": max_count,
            "reason": reason,
        }

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
        # 🆕 برای super-task (source=auto_consolidation یا merged_from non-empty)
        # یا raw_idea خیلی بزرگ، optimizations اعمال می‌کنیم تا از Render edge
        # timeout (30s) جلوگیری شود.
        # detection محکم — هر کدام از این سه شواهد یعنی super-task:
        is_super_task = (
            getattr(task, "source", "") == "auto_consolidation"
            or bool(getattr(task, "merged_from", []) or [])
            or bool(getattr(task, "consolidation_meta", None))
        )
        is_heavy = is_super_task or len(raw) > 5000
        # diagnostic log — حتماً visible در Render logs
        logger.info(
            f"regenerate START: task={task_id[:8]}, "
            f"source={getattr(task, 'source', '?')}, "
            f"merged_from_count={len(getattr(task, 'merged_from', []) or [])}, "
            f"consolidation_meta={'yes' if getattr(task, 'consolidation_meta', None) else 'no'}, "
            f"is_super_task={is_super_task}, "
            f"raw_len={len(raw)}, "
            f"path={'INSTANT' if is_super_task else ('FAST' if is_heavy else 'NORMAL')}"
        )

        # 🆕 super-task **instant fast-path** — بدون AI call.
        # برای super-task ها content قبلاً ساختاریافته است (consolidation
        # منطقی پیش‌نیاز را انجام داده). regenerate کاربر معمولاً برای ارتقای
        # یک تسک قدیمی به نسخهٔ جدید EXECUTOR_DISCLAIMER است (مثلاً اضافه
        # شدن بخش وابستگی‌ها). انجام full AI regenerate در این حالت ضرورت
        # ندارد و باعث Render timeout می‌شود.
        # روند instant:
        #   1) متن body را از task.prompt قدیمی استخراج کن (بدون disclaimer قدیمی)
        #   2) EXECUTOR_DISCLAIMER جدید را prepend کن
        #   3) raw_idea را به‌عنوان منبع نگه‌دار
        #   4) AI صدا زده نمی‌شود — instant
        if is_super_task:
            from .oversight_strong_prompt import EXECUTOR_DISCLAIMER
            old_prompt = task.prompt or ""
            # disclaimer قدیمی را strip کن (هر نسخه‌ای)
            old_header = "## ⚠️ یادداشت مهم برای مدل اجراکننده"
            if old_header in old_prompt:
                # پیدا کن کجا disclaimer تمام می‌شود (آخرین --- قبل از body اصلی)
                # disclaimer همیشه با یک خط "---" به پایان می‌رسد
                idx = old_prompt.find(old_header)
                if idx >= 0:
                    # پیدا کن "---" پایانی disclaimer (اولین --- بعد از header)
                    end_marker = old_prompt.find("\n---\n", idx)
                    if end_marker > 0:
                        body = old_prompt[end_marker + len("\n---\n"):].lstrip()
                    else:
                        body = old_prompt[idx + len(old_header):].lstrip()
                else:
                    body = old_prompt
            else:
                body = old_prompt
            new_prompt = EXECUTOR_DISCLAIMER + "\n" + body
            logger.info(
                f"regenerate (instant fast-path super-task): task={task_id[:8]}, "
                f"old_len={len(old_prompt)}, new_len={len(new_prompt)}"
            )
            new_data = {
                "prompt": new_prompt,
                "title": task.title,
                "target_files": task.target_files,
                "acceptance_criteria": task.acceptance_criteria,
                "task_steps": task.task_steps,
            }
        else:
            _mp_mode = "never" if is_heavy else "auto"
            _skip_deep = is_heavy
            try:
                new_data = await self.idea_to_prompt(
                    idea=raw,
                    watched_id=task.watched_id,
                    type_=task.type,
                    priority=task.priority,
                    model_id=model_id,
                    model_ids=model_ids,
                    multi_pass_mode=_mp_mode,
                    _skip_deep_context=_skip_deep,
                    # 🆕 (Reference Projects) — هنگام regenerate، انتخاب‌های
                    # قبلیِ تسک باید حفظ شوند تا fusion text در پرامپت جدید هم
                    # حضور داشته باشد. در غیر این صورت، regenerate مرجع‌ها را
                    # silently دور می‌انداخت.
                    selected_projects=list(task.selected_projects or []) or None,
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
                # 🔬 (Runtime Verify Stage 1) — همیشه AC را normalize کن
                try:
                    from .verify_runtime import normalize_ac_list
                    task.acceptance_criteria = normalize_ac_list(new_ac)
                except Exception:
                    task.acceptance_criteria = new_ac
            # 🆕 (Multi-pass Checklist) — task_steps را به‌روز کن
            new_steps = new_data.get("task_steps") or []
            if new_steps:
                task.task_steps = new_steps
                task.overall_completion_pct = 0  # reset
            if model_id:
                task.models_used = [model_id]
            task.updated_at = now_iso()
            self._save_tasks()
            # 🆕 (Prompt-GitHub Sync) — همگام‌سازی خودکار توسط _save_tasks
            logger.info(
                f"regenerate DONE: task={task_id[:8]}, "
                f"new_prompt_len={len(task.prompt)}, "
                f"saved + sync triggered"
            )
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
            # 🆕 (AI Usage) آمار مصرف ۷ روز اخیر + موجودی provider ها
            "ai_usage": self._compute_ai_usage_summary(),
        }

    def _compute_ai_usage_summary(self) -> Dict[str, Any]:
        """خلاصهٔ مصرف AI برای daily report (۷ روز اخیر + balances)."""
        try:
            from .ai_balance_service import AIBalanceService
            from datetime import timedelta as _td
            from .ai_log_helper import query_ai_usage_summary  # type: ignore
        except Exception:
            # ai_log_helper اختیاری — اگر نبود، inline query
            pass
        result: Dict[str, Any] = {
            "week_tokens": 0,
            "week_cost_usd": 0.0,
            "week_request_count": 0,
            "top_providers": [],
            "balances": {},
        }
        try:
            from datetime import datetime, timedelta
            from .ai_balance_service import AIBalanceService
            from ..core.database import SessionLocal
            from ..models.ai_log import AILog
            from sqlalchemy import func
            since = datetime.utcnow() - timedelta(days=7)
            db = SessionLocal()
            try:
                # totals
                row = db.query(
                    func.count(AILog.id),
                    func.sum(AILog.total_tokens),
                    func.sum(AILog.cost),
                ).filter(AILog.created_at >= since).first()
                if row:
                    result["week_request_count"] = int(row[0] or 0)
                    result["week_tokens"] = int(row[1] or 0)
                    result["week_cost_usd"] = round(float(row[2] or 0), 4)
                # top 3 providers
                prov_rows = db.query(
                    AILog.provider,
                    func.sum(AILog.total_tokens),
                    func.sum(AILog.cost),
                ).filter(AILog.created_at >= since).group_by(AILog.provider).order_by(
                    func.sum(AILog.total_tokens).desc()
                ).limit(3).all()
                result["top_providers"] = [
                    {
                        "provider": r[0],
                        "tokens": int(r[1] or 0),
                        "cost": round(float(r[2] or 0), 4),
                    }
                    for r in prov_rows
                ]
            finally:
                db.close()
            # balances
            try:
                result["balances"] = AIBalanceService.get_all_balances() or {}
            except Exception as _be:
                logger.debug(f"_compute_ai_usage_summary balances skip: {_be}")
        except Exception as e:
            logger.debug(f"_compute_ai_usage_summary failed: {e}")
        return result

    # ====================================================================
    # Idea -> Strong Prompt
    # ====================================================================
    # 🆕 (C5) — Title management: validator + reassess
    # ====================================================================

    @staticmethod
    def _record_title_change(
        task: "OversightTask",
        old_title: str,
        new_title: str,
        source: str,
        reason: Optional[str] = None,
    ) -> None:
        """ثبت یک تغییر عنوان در title_history روی task.

        🆕 (C5 — مرحلهٔ ۶) — تابع متمرکز برای ثبت تاریخچهٔ تغییر عنوان.
        قبلاً این منطق در ۲ جای جداگانه (update_task و _ai_reassess_title)
        تکرار شده بود. حالا همگی از این تابع استفاده می‌کنند.

        source: "manual" | "ai_generate" | "verify_reassess" | "regenerate"
                | "consolidation"
        """
        if not new_title or new_title == old_title:
            return
        try:
            entry: Dict[str, Any] = {
                "ts": now_iso(),
                "source": str(source or "unknown")[:40],
                "old_title": str(old_title or "")[:200],
                "new_title": str(new_title or "")[:200],
            }
            if reason:
                entry["reason"] = str(reason)[:300]
            _hist = list(getattr(task, "title_history", None) or [])
            _hist.append(entry)
            # حداکثر ۲۰ آیتم نگه‌داری (FIFO)
            task.title_history = _hist[-20:]
        except Exception as _e:
            logger.debug(f"_record_title_change failed for {getattr(task, 'id', '?')}: {_e}")

    # کلمات generic که اگر تنها token معنادار عنوان باشند، عنوان "نا‌مفهوم" تلقی
    # می‌شود و retry تولید عنوان اتفاق می‌افتد.
    _TITLE_GENERIC_TOKENS = {
        # فارسی
        "بهبود", "تغییر", "تغییرات", "سیستم", "پروژه", "اصلاح", "اصلاحات",
        "رفع", "ایجاد", "ساخت", "اضافه", "حذف", "اپدیت", "آپدیت", "بروزرسانی",
        # انگلیسی
        "fix", "update", "improve", "improvement", "change", "changes",
        "add", "remove", "system", "project", "task", "feature", "bug",
        "refactor", "tweak", "patch",
    }

    @classmethod
    def _validate_title_quality(cls, title: str) -> bool:
        """آیا این عنوان به‌اندازهٔ کافی توصیفی هست؟

        قواعد رد:
          - خالی یا < 3 کاراکتر
          - فقط شامل کلمات generic (مثل "fix" یا "بهبود سیستم")
          - بیش از 80 درصد tokenهایش generic باشند

        True: عنوان قابل قبول است.
        False: نیاز به retry/regenerate.
        """
        import re as _re
        if not title or not title.strip():
            return False
        clean = title.strip()
        if len(clean) < 3:
            return False
        # tokenize ساده — split روی whitespace + punctuation
        tokens = [
            t.lower().strip(".,؛:!?()[]{}«»\"'")
            for t in _re.split(r'[\s\-،,]+', clean)
            if t.strip()
        ]
        if not tokens:
            return False
        # اگر تعداد token < 2 و token تنها generic است → رد
        meaningful = [t for t in tokens if t and t not in cls._TITLE_GENERIC_TOKENS]
        if not meaningful:
            return False
        # اگر بیش از 80٪ tokenها generic → رد
        if len(tokens) >= 3:
            generic_ratio = (len(tokens) - len(meaningful)) / len(tokens)
            if generic_ratio > 0.8:
                return False
        return True

    async def _ai_reassess_title(
        self,
        task: "OversightTask",
        *,
        triggered_by: str = "verify_reassess",
        model_id: Optional[str] = None,
    ) -> Optional[str]:
        """بازنگری عنوان تسک با AI سبک.

        🆕 (C5 — بند ۱۱) — بعد از هر verify (single/bulk، fast/deep) و بعد از
        build super-task فراخوانی می‌شود. اگر AI تصمیم بگیرد عنوان فعلی
        مناسب نیست، پیشنهاد جدید برمی‌گرداند.

        قاعدهٔ skip:
          - اگر manual_title_override == True → skip کامل (احترام به کاربر)

        خروجی: new_title اگر تغییر کرد، None اگر keep یا fail.
        side effect: title و title_history روی task به‌روز می‌شوند و
        _save_tasks() صدا زده می‌شود.
        """
        if getattr(task, "manual_title_override", False):
            return None
        try:
            from .ai_manager import get_ai_manager
            from .ai_base import Message
        except Exception:
            return None
        if not model_id:
            try:
                from ..core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
                model_id = DEFAULT_EXTRACTION_MODEL_ID
            except Exception:
                return None

        # جمع‌آوری context
        _ac_list = []
        for ac in (getattr(task, "acceptance_criteria", None) or [])[:8]:
            if isinstance(ac, str):
                _ac_list.append(ac[:200])
            elif isinstance(ac, dict):
                _ac_list.append(str(ac.get("text") or "")[:200])
        _completed = []
        _remaining = []
        for s in (getattr(task, "task_steps", None) or [])[:15]:
            if not isinstance(s, dict):
                continue
            _t = str(s.get("title") or "")[:120]
            _st = str(s.get("status") or "").lower()
            if _st == "done":
                _completed.append(_t)
            else:
                _remaining.append(_t)

        prompt_text = (
            "وظیفه‌ات: ارزیابی عنوان فعلی تسک و تصمیم اینکه آیا باید عوض شود.\n\n"
            f"عنوان فعلی: \"{task.title}\"\n"
            f"اولویت: {task.priority}\n"
            f"وضعیت: {task.status}\n"
            f"verification_status: {task.verification_status}\n"
            f"acceptance_criteria ({len(_ac_list)}):\n"
            + "\n".join(f"  - {a}" for a in _ac_list[:6]) + "\n"
            f"\nمراحل done شده ({len(_completed)}):\n"
            + "\n".join(f"  ✓ {s}" for s in _completed[:6]) + "\n"
            f"\nمراحل remaining ({len(_remaining)}):\n"
            + "\n".join(f"  ○ {s}" for s in _remaining[:6]) + "\n"
            f"\nlast_summary: {(task.last_summary or '')[:300]}\n\n"
            "قواعد:\n"
            "1. اگر عنوان فعلی **دقیق، توصیفی (حداکثر ۸ کلمه)، با فعل عملیاتی + "
            "موضوع مشخص** است → `keep`.\n"
            "2. اگر عنوان generic است (مثل 'بهبود سیستم'، 'fix'، 'تغییرات') یا "
            "از وضعیت/AC ها انحراف دارد → عنوان مناسب پیشنهاد بده.\n"
            "3. در پیشنهاد جدید، حداکثر ۸ کلمه، با فعل عملیاتی + موضوع.\n\n"
            "خروجی JSON خالص:\n"
            "{\"action\": \"keep\" | \"update\", \"new_title\": \"...\", \"reason\": \"...\"}"
        )

        try:
            import asyncio as _asyncio
            mgr = get_ai_manager()
            resp = await _asyncio.wait_for(
                mgr.generate(
                    model_id=model_id,
                    messages=[Message(role="user", content=prompt_text)],
                    max_tokens=200,
                    temperature=0.2,
                    allow_fallback=True,
                ),
                timeout=15,
            )
            raw = (resp.content or "").strip()
        except _asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.debug(f"_ai_reassess_title failed: {e}")
            return None

        import json as _json
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = _json.loads(raw[start:end + 1])
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        action = str(data.get("action") or "keep").lower().strip()
        if action != "update":
            return None
        new_title = str(data.get("new_title") or "").strip()
        if not new_title or new_title == task.title:
            return None
        # validator: اگر AI عنوان بد پیشنهاد داد، نگه نمی‌داریم
        if not self._validate_title_quality(new_title):
            return None
        # اعمال و ثبت در history via _record_title_change
        async with self._lock:
            _old = task.title
            task.title = new_title[:200]
            self._record_title_change(
                task, _old, task.title,
                source=triggered_by,
                reason=str(data.get("reason") or "")[:300] or None,
            )
            task.updated_at = now_iso()
            self._save_tasks()
        return new_title


    async def _generate_better_title(
        self,
        idea: str,
        prompt: str,
        fallback: str,
        model_id: Optional[str] = None,
    ) -> Optional[str]:
        """تولید عنوان بهتر وقتی validator اولیه رد می‌کند.

        🆕 (C5 — بند ۹) — AI call سبک با hint قوی برای کلمات غیر-generic.
        خروجی: عنوان جدید یا None در صورت خطا.
        """
        try:
            from .ai_manager import get_ai_manager
            from .ai_base import Message
        except Exception:
            return None
        if not model_id:
            try:
                from ..core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
                model_id = DEFAULT_EXTRACTION_MODEL_ID
            except Exception:
                return None

        prompt_text = (
            "وظیفه‌ات: بر اساس ایده و پرامپت زیر، یک **عنوان توصیفی** برای تسک "
            "بساز. عنوان قبلی generic بود و قابل قبول نیست.\n\n"
            "قواعد سخت:\n"
            "1. حداکثر ۸ کلمه\n"
            "2. ساختار: 'فعل عملیاتی + موضوع مشخص + scope روشن'\n"
            "3. **ممنوع**: کلمات کلی مثل 'بهبود'، 'تغییر'، 'سیستم'، 'fix'، "
            "'update'، 'improve' بدون context.\n"
            "4. باید **چه چیزی** عوض می‌شود و **روی کدام بخش** اشاره شود.\n\n"
            f"ایده: {idea[:1500]}\n\n"
            f"پرامپت: {prompt[:2500]}\n\n"
            f"عنوان قبلی (نا‌مفهوم — جایگزین کن): \"{fallback}\"\n\n"
            "خروجی فقط یک خط متن — عنوان جدید (بدون quote، بدون JSON)."
        )

        try:
            import asyncio as _asyncio
            mgr = get_ai_manager()
            resp = await _asyncio.wait_for(
                mgr.generate(
                    model_id=model_id,
                    messages=[Message(role="user", content=prompt_text)],
                    max_tokens=80,
                    temperature=0.3,
                    allow_fallback=True,
                ),
                timeout=12,
            )
            raw = (resp.content or "").strip()
        except _asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.debug(f"_generate_better_title failed: {e}")
            return None

        # cleanup: حذف quote، خطوط اضافی
        new_title = raw.split("\n")[0].strip(' "\'`')[:120]
        if not new_title:
            return None
        # validate نهایی — اگر باز هم generic بود، fallback را بازگردان (None)
        if not self._validate_title_quality(new_title):
            return None
        return new_title


    # ====================================================================

    @staticmethod
    def _is_complex_idea(idea: str) -> bool:
        """تشخیص اینکه ایده پیچیده/طولانی است و نیاز به multi-pass دارد.

        معیارها (هر کدام True باشد، complex است):
          - طول > 400 کاراکتر
          - بیش از ۸ خط
          - بیش از ۳ علامت bullet (- * • ۱. 1.)
          - بیش از ۴ علامت گذاری مرتبط (;، .، \n\n)
          - بیش از ۲ URL متفاوت
        """
        import re as _re
        if not idea or not idea.strip():
            return False
        if len(idea) > 400:
            return True
        if idea.count("\n") > 7:
            return True
        bullets = len(_re.findall(r'(?m)^\s*(?:[-*•]|\d+[\.\)])\s+', idea))
        if bullets > 3:
            return True
        urls = _re.findall(r'https?://[^\s\)\]\}]+', idea)
        if len(set(urls)) > 2:
            return True
        # شمارش "و" و "همچنین" و "بعد" به‌عنوان indicator مراحل
        connectors = sum(idea.count(w) for w in [
            "همچنین", "بعد از", "علاوه", "ضمناً", "نکته:", "اول", "دوم", "سوم",
            "اضافه کن", "اصلاح کن", "تغییر بده", "حذف کن",
        ])
        if connectors >= 4:
            return True
        return False

    async def _ai_plan_steps_from_idea(
        self,
        idea: str,
        user_goal: str,
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """مرحله ۱ از multi-pass: تقسیم ایده طولانی به مراحل کوچک.

        خروجی: list از مراحل، هرکدام شامل:
          {id, title, scope, raw_excerpt, key_terms: [...]}
        اگر AI نتوانست تقسیم منطقی بدهد، list خالی.
        """
        # 🆕 (Phase 5 — bug 30) — Pre-detect explicit section markers in idea.
        # برای ایده‌های خیلی بزرگ مثل meta-task ها که چندین Phase/فاز دارند،
        # AI تمایل دارد همه را یک task کلی ببیند و فقط ۱-۲ step بسازد.
        # با شناسایی صریح بخش‌بندی‌ها، AI را مجبور می‌کنیم پیروی کند.
        import re as _re_seg

        # 🆕 (bug 30 v4) — Reference/historical marker detection.
        # وقتی متن کاربر می‌گوید «فاز X قبلاً اجرا شده» یا «مرور سریع» یا
        # «(done)» یا «برای مرجع»، آن section باید از step generation حذف شود
        # — وگرنه bloat با کارهای انجام‌شده ایجاد می‌شود.
        _REFERENCE_MARKERS = [
            r'قبلاً\s+(?:اجرا|انجام|پیاده)\s*شد',
            r'پیش[\s\-]?تر\s+(?:اجرا|انجام|پیاده)\s*شد',
            r'(?:فقط|صرفاً)\s+(?:برای|جهت)\s+(?:مرجع|حافظه|reference|reminder)',
            r'مرور\s+(?:سریع|کوتاه|قبلی)',
            r'\(\s*(?:done|completed|تمام|تمام\s*شد|انجام\s*شد|اجرا\s*شد)\s*\)',
            r'(?:این\s+بخش|بخش\s+(?:الف|قبل|قدیم)|previous\s+phase).*قبلاً',
            r'^\s*✅\s+(?:Phase|فاز|Stage)\s+[\d]+',  # «✅ Phase 1 اضافه کرد»
            r'(?:چه\s+چیزی|چیزی\s+که)\s+(?:الان|حالا)\s+داریم',
            r'(?:خلاصه|recap|summary)\s+(?:از|of)\s+(?:Phase|فاز|stages?)',
        ]
        _section_patterns = [
            # heading-level English: "## Phase 1", "### Stage 2", etc.
            r'(?im)^\s*#{1,4}\s*[^\w\n]*(?:phase|stage|step)\s+[\d]+',
            # inline English with separator: "Phase 1 — ...", "Stage 2:"
            r'(?im)^\s*(?:phase|stage|step)\s+[\d]+\s*[:\-—]',
            # Persian with letter-emoji prefix: "## 🅰️ فاز ۱"
            r'(?im)^\s*#{1,4}\s*[🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹]️?\s*فاز\s*[\d۰-۹]+',
            # Persian heading: "## فاز ۱", "# فاز ۲"
            r'(?im)^\s*#{1,4}\s*[^\w\n]*فاز\s*[\d۰-۹]+',
            # Persian word form: "فاز دوم:", "فاز سوم:"
            r'(?im)^\s*فاز\s+(?:اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|یازدهم|دوازدهم)\s*[:\-—]',
            # Generic Persian: "مرحله ۱:", "گام ۲:"
            r'(?im)^\s*(?:مرحله|گام)\s*[\d۰-۹]+\s*[:\-—]',
            # 🆕 (bug 30 — refinement) heading شامل Phase X با هر متن قبلش
            # مثل "# 🎯 پرامپت Phase 1 — ..."
            r'(?im)^\s*#{1,4}\s.*?\b(?:phase|stage)\s+[\d]+\b',
            # 🆕 (bug 30 v3) — Bug C\d / Bug \d الگو (مثل "# Bug C6", "## Bug 30")
            r'(?im)^\s*#{1,4}\s*[^\w\n]*\b[Bb]ug\s+[Cc]?[\d]+\b',
            # 🆕 (bug 30 v3) — فیکس فارسی (مثل "## فیکس ۱", "### فیکس ۲")
            r'(?im)^\s*#{1,4}\s*[^\w\n]*فیکس\s*[\d۰-۹]+',
            r'(?im)^\s*فیکس\s+[\d۰-۹]+\s*[:\-—]',
            # 🆕 (bug 30 v3) — "بهبود ۱", "گپ ۱"، "ستون A", "Chunk N"
            r'(?im)^\s*#{0,4}\s*[^\w\n]*بهبود\s+[\d۰-۹]+',
            r'(?im)^\s*#{0,4}\s*[^\w\n]*گپ\s+[\d۰-۹]+',
            r'(?im)^\s*#{0,4}\s*[^\w\n]*ستون\s+[A-Zا-ی]',
            r'(?im)^\s*#{0,4}\s*\bChunk\s+[\d]+\b',
            # 🆕 (bug 30 v3) — markdown heading عمومی به‌عنوان fallback نهایی
            # هر # یا ## یا ### که با emoji یا متن شروع شود (الویت پایین‌تر)
            # این موقع‌ای فعال می‌شود که هیچ کدام از patterns بالا کافی نباشد
            r'(?im)^\s*##\s+[🎯🔬🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🚀🔧📌💡⭐🧪✅🚫⚠📁🏗🔄🛡📊🧠]+',
            r'(?im)^\s*#\s+[🎯🔬🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🚀🔧📌💡⭐🧪✅🚫⚠📁🏗🔄🛡📊🧠]+',
        ]
        # 🆕 (bug 30 v2) — استخراج موقعیت + متن header برای chunking
        _section_starts: List[Tuple[int, str]] = []  # (offset, header_line)
        _seen_offsets: set = set()
        for _pat in _section_patterns:
            for _m in _re_seg.finditer(_pat, idea):
                _off = _m.start()
                # حذف overlap نزدیک (همان خط با چند regex)
                _too_close = any(abs(_off - o) < 5 for o in _seen_offsets)
                if _too_close:
                    continue
                _seen_offsets.add(_off)
                _header = _re_seg.sub(r'\s+', ' ', _m.group(0).strip())[:120]
                _section_starts.append((_off, _header))
        _section_starts.sort(key=lambda x: x[0])

        # 🆕 (bug 30 v4) — Filter out reference/historical sections (+ inheritance).
        # هر section که در ۵۰۰ کاراکتر اول خود یکی از markers بالا را داشته
        # باشد، به‌عنوان reference تگ می‌شود و از step generation خارج می‌شود.
        # علاوه بر این، اگر یک parent section reference بود، همه sub-sectionهای
        # داخل آن (تا section بعدی هم‌سطح یا بالاتر) نیز skip می‌شوند.
        def _section_is_reference(start_off: int, end_off: int) -> bool:
            preview = idea[start_off:min(end_off, start_off + 500)]
            for _rm in _REFERENCE_MARKERS:
                if _re_seg.search(_rm, preview, _re_seg.IGNORECASE):
                    return True
            return False

        def _heading_level(header: str) -> int:
            """تعداد # در شروع header — اگر header اصلاً heading نباشد، 99."""
            _hm = _re_seg.match(r'^\s*(#+)', header)
            return len(_hm.group(1)) if _hm else 99

        # اول هر section را به‌طور مستقیم چک کن
        _direct_ref: List[bool] = []
        for _idx, (_off, _header) in enumerate(_section_starts):
            _end = (
                _section_starts[_idx + 1][0]
                if _idx + 1 < len(_section_starts)
                else len(idea)
            )
            _direct_ref.append(_section_is_reference(_off, _end))

        # حالا inheritance: اگر section[i] direct ref است و heading level دارد،
        # هر section بعدی با level > آن تا section دیگر با level ≤ آن نیز ref است.
        _is_ref_final: List[bool] = list(_direct_ref)
        for _i, _drf in enumerate(_direct_ref):
            if not _drf:
                continue
            _parent_level = _heading_level(_section_starts[_i][1])
            if _parent_level >= 99:
                continue  # heading-less section نمی‌تواند parent باشد
            # walk forward and mark descendants
            for _j in range(_i + 1, len(_section_starts)):
                _child_level = _heading_level(_section_starts[_j][1])
                if _child_level <= _parent_level:
                    break  # رسیدیم به sibling یا سطح بالاتر
                _is_ref_final[_j] = True

        _filtered_starts: List[Tuple[int, str]] = []
        _skipped_ref_count = 0
        for _idx, (_off, _header) in enumerate(_section_starts):
            if _is_ref_final[_idx]:
                _skipped_ref_count += 1
                continue
            _filtered_starts.append((_off, _header))
        if _skipped_ref_count > 0:
            logger.info(
                f"_ai_plan_steps: skipped {_skipped_ref_count} reference/"
                f"historical sections (already-done markers + inheritance)"
            )
        _section_starts = _filtered_starts

        # 🆕 (bug 30 v4) — Programmatic enumerated sub-list expansion.
        # وقتی یک section شامل لیست شماره‌دار/بولت با ≥۳ آیتم explicit است
        # (مثل «Chunk 1..8»، «گپ ۱..۶»، «بهبود ۷..۹»)، آن lista را به sub-step
        # جداگانه expand می‌کنیم تا هر آیتم خودش یک step شود.
        # 🆕 (bug 30 v4) — Patterns هم فرمت bold (`**Chunk N**`) و هم numbered
        # prefix (`1. `) را می‌پذیرند. بخش lead = "1. **" یا "- **" یا "" قبل از
        # کلید واژه قرار می‌گیرد. asterisks تا ۲ تا قبل و بعد عبارت مجاز است.
        _LEAD = r'(?:[\d۰-۹]+[\.\)]\s+|[-*•]\s+)?\*{0,2}\s*'
        _TAIL = r'\*{0,2}\s*[:\-—\.\*]'
        _ENUM_PATTERNS = [
            # "Chunk N: ..." یا "1. **Chunk N**: ..." یا "**Chunk N** — ..."
            rf'(?im)^\s*{_LEAD}\bChunk\s+([\d]+)\s*{_TAIL}',
            # "گپ ۱ — ...", "گپ N:"، "1. **گپ ۱**: "
            rf'(?im)^\s*{_LEAD}گپ\s+([\d۰-۹]+)\s*{_TAIL}',
            # "بهبود ۷ — ..."
            rf'(?im)^\s*{_LEAD}بهبود\s+([\d۰-۹]+)\s*{_TAIL}',
            # "فیکس ۱ — ..."
            rf'(?im)^\s*{_LEAD}فیکس\s+([\d۰-۹]+)\s*{_TAIL}',
            # "Bug C6 — ..." (با heading hashes اختیاری)
            r'(?im)^\s*#{0,4}\s*[^\w\n]*\b[Bb]ug\s+[Cc]?([\d]+)\b\s*[:\-—\.]',
            # "مرحله X:" (وقتی sub-list هست)
            rf'(?im)^\s*{_LEAD}مرحله\s+([\d۰-۹]+)\s*[:\-—]',
            # 🆕 AC جدول/لیست: "AC 1:", "AC#1", "| 1 | ... |" در جدول AC
            rf'(?im)^\s*{_LEAD}AC\s*#?\s*([\d]+)\s*[:\-—]',
            # 🆕 "edge case N", "Stage N" در sub-list
            rf'(?im)^\s*{_LEAD}(?:edge\s*case|stage)\s+([\d]+)\s*{_TAIL}',
        ]

        def _expand_section_enums(start_off: int, end_off: int, header: str) -> List[Tuple[int, str]]:
            """اگر داخل یک section لیست شماره‌دار با ≥۳ آیتم بود، آن آیتم‌ها
            را به‌عنوان sub-section برمی‌گرداند. اگر نه، [] برمی‌گرداند."""
            section_text = idea[start_off:end_off]
            for _ep in _ENUM_PATTERNS:
                _matches = list(_re_seg.finditer(_ep, section_text))
                if len(_matches) >= 3:
                    _subs: List[Tuple[int, str]] = []
                    for _m in _matches:
                        _abs_off = start_off + _m.start()
                        _line = _re_seg.sub(r'\s+', ' ', _m.group(0).strip())[:120]
                        # عنوان sub-section را با header parent ترکیب کن
                        _sub_header = f"{header[:60]} :: {_line}"[:180]
                        _subs.append((_abs_off, _sub_header))
                    return _subs
            return []

        _expanded_starts: List[Tuple[int, str]] = []
        _expanded_from_sections = 0
        for _idx, (_off, _header) in enumerate(_section_starts):
            _end = (
                _section_starts[_idx + 1][0]
                if _idx + 1 < len(_section_starts)
                else len(idea)
            )
            _subs = _expand_section_enums(_off, _end, _header)
            if _subs:
                _expanded_starts.extend(_subs)
                _expanded_from_sections += 1
            else:
                _expanded_starts.append((_off, _header))
        if _expanded_from_sections > 0:
            _delta = len(_expanded_starts) - len(_section_starts)
            logger.info(
                f"_ai_plan_steps: expanded {_expanded_from_sections} section(s) "
                f"with enumerated sub-lists → +{_delta} sub-steps"
            )
        _section_starts = sorted(_expanded_starts, key=lambda x: x[0])

        # 🆕 (bug 30 v4) — Identifier extraction from raw idea.
        # نام فایل‌ها/کلاس‌ها/توابع و paths را استخراج می‌کنیم تا AI به جای
        # اختراع نام، از همین‌ها در key_terms و target_files استفاده کند.
        def _extract_identifiers(text: str) -> Dict[str, List[str]]:
            ids = {"paths": [], "classes": [], "functions": [], "endpoints": []}
            # file paths (backend/.../*.py، frontend/.../*.tsx، docs/*.md و …)
            for _m in _re_seg.finditer(
                r'\b((?:backend|frontend|docs|tests|src|app|scripts)/[\w/\.\-]+\.(?:py|tsx?|jsx?|md|json|yaml|yml|sh|toml|env))\b',
                text,
            ):
                _p = _m.group(1)
                if _p not in ids["paths"]:
                    ids["paths"].append(_p)
            # PascalCase class names + suffixes معمول
            for _m in _re_seg.finditer(
                r'\b([A-Z][a-zA-Z0-9]{3,}(?:Service|Helper|Probe|Verifier|Manager|Bundle|Context|Config|Session|Detector|Analyzer|Extractor|Result|Schema|Runner|Cache|Orchestrator|Builder|Searcher|Inventory))\b',
                text,
            ):
                _c = _m.group(1)
                if _c not in ids["classes"]:
                    ids["classes"].append(_c)
            # snake_case function/method names (با حداقل یک underscore)
            for _m in _re_seg.finditer(
                r'\b(_?[a-z][a-z0-9]*(?:_[a-z0-9]+){1,})\b',
                text,
            ):
                _f = _m.group(1)
                # حذف کلمات common که snake_case نیستن
                if (
                    len(_f) >= 6
                    and _f not in ids["functions"]
                    and _f not in ("user_goal", "user_id", "task_id", "watched_id")
                ):
                    ids["functions"].append(_f)
            # HTTP endpoints مثل GET /api/X یا /verify-trace
            for _m in _re_seg.finditer(
                r'\b(?:GET|POST|PUT|PATCH|DELETE)\s+(/[\w\-/\{\}\:]+)|^\s*(/api/[\w\-/\{\}\:]+)',
                text,
                _re_seg.MULTILINE,
            ):
                _ep = _m.group(1) or _m.group(2)
                if _ep and _ep not in ids["endpoints"]:
                    ids["endpoints"].append(_ep)
            # caps
            return {
                "paths": ids["paths"][:60],
                "classes": ids["classes"][:60],
                "functions": ids["functions"][:80],
                "endpoints": ids["endpoints"][:40],
            }

        _extracted_ids = _extract_identifiers(idea)

        _detected_sections = [h for _, h in _section_starts]
        _section_count = len(_detected_sections)
        _is_multi_section = _section_count >= 3

        # 🆕 (bug 30) — اگر بخش‌بندی صریح زیاد دیدیم، prompt را hint بزن
        # و فرمت compact بخواه تا output در ۱۲۰۰۰ توکن جای کافی داشته باشد.
        # 🔴 (extraction-100pct-fix) — اگر idea بزرگه (>200KB، نشانهٔ
        # attachment غول‌پیکر)، compact-hint رو **حذف** می‌کنیم — اجازه می‌دیم
        # AI به اندازهٔ نیاز scope و raw_excerpt بزرگ بنویسه. کاربر گفت
        # «هزینه مهم نیست» و output budget هم به 64K بومپ شده.
        _has_huge_attachment = len(idea) > HUGE_IDEA_CHARS
        _section_hint = ""
        if _is_multi_section:
            # 🆕 (bug 30 v3) — همهٔ sections را به AI نشان بده (cap 200)
            _detected_preview = "\n".join(
                f"  - {s[:80]}" for s in _detected_sections[:200]
            )
            _section_hint = (
                f"\n\n🚨 **تشخیص خودکار: متن کاربر شامل {_section_count} "
                f"بخش صریح است.** بخش‌های detected:\n{_detected_preview}\n\n"
                f"⚠️ **الزامی**: تو **باید دقیقاً {min(_section_count, 200)} "
                f"مرحله** بسازی، هر کدام مربوط به یکی از این بخش‌های صریح. "
                f"اگر تعداد کمتر برگردانی، یعنی کار را خلاصه کرده‌ای — این "
                f"اشتباه است.\n\n"
            )
            if _has_huge_attachment:
                # حالت attachment بزرگ — اجازه به AI که verbose باشه
                # 🔴 v2: caps هماهنگ با field truncation در step builder
                # (scope[:5000], raw_excerpt[:15000]) — قبلاً 20K/50K بود
                # که overflow output budget می‌شد.
                _per_step_scope = min(5000, max(500, len(idea) // max(_section_count, 1)))
                _section_hint += (
                    f"💡 **این متن شامل فایل پیوست بزرگ است ({len(idea):,} char). "
                    f"کاربر صریحاً گفت «هیچ بخش drop نکن، خلاصه‌سازی مخرب ممنوع».**\n"
                    f"- scope هر مرحله: **حداکثر {_per_step_scope:,} char**\n"
                    f"- raw_excerpt: **عیناً متن آن بخش (تا 15KB در صورت نیاز)**\n"
                    f"- اگر یک بخش بیشتر از این می‌خواهد، آن را به sub-steps "
                    f"بشکن (مرحله 4.1، 4.2، ...) — نه drop\n"
                    f"- هرگز «و موارد مشابه» یا «خلاصه» ننویس — verbatim کامل\n"
                )
            else:
                _section_hint += (
                    f"💡 **برای جا کردن همه در پاسخ**: scope هر مرحله را **حداکثر "
                    f"۴۰۰ کاراکتر** و raw_excerpt را **حداکثر ۸۰۰ کاراکتر** "
                    f"نگه‌دار. غنی‌سازی در pass بعدی انجام می‌شود."
                )
            if _skipped_ref_count > 0:
                _section_hint += (
                    f"\n\n🚫 **{_skipped_ref_count} بخش 'مرور/قبلاً اجرا شده' "
                    f"حذف شدند** — برای آنها step نساز (کارشان تمام است). "
                    f"فقط روی بخش‌های detected بالا تمرکز کن."
                )

        # 🆕 (bug 30 v4) — Identifier hint: list خروجی regex را به AI نشان بده
        # تا از همان نام‌ها استفاده کند، نه اختراع کند.
        _id_hint = ""
        if any(_extracted_ids[k] for k in ("paths", "classes", "functions", "endpoints")):
            _id_lines: List[str] = []
            if _extracted_ids["paths"]:
                _id_lines.append(
                    "📂 مسیرهای فایل ذکرشده در متن (عیناً استفاده کن — اختراع نکن):"
                )
                for _p in _extracted_ids["paths"][:30]:
                    _id_lines.append(f"   • {_p}")
            if _extracted_ids["classes"]:
                _id_lines.append(
                    "🏷 نام کلاس‌های ذکرشده (در key_terms و scope استفاده کن):"
                )
                for _c in _extracted_ids["classes"][:30]:
                    _id_lines.append(f"   • {_c}")
            if _extracted_ids["functions"]:
                _id_lines.append(
                    "⚙ نام توابع/متغیرهای snake_case ذکرشده:"
                )
                for _f in _extracted_ids["functions"][:40]:
                    _id_lines.append(f"   • {_f}")
            if _extracted_ids["endpoints"]:
                _id_lines.append("🌐 endpoint های ذکرشده:")
                for _ep in _extracted_ids["endpoints"][:20]:
                    _id_lines.append(f"   • {_ep}")
            _id_hint = (
                "\n\n📌 **identifier های استخراج‌شده از متن کاربر**:\n"
                + "\n".join(_id_lines)
                + "\n\n⚠️ **قاعدهٔ سخت**: در `key_terms`, `target_files`, و "
                "`scope` فقط از همین نام‌ها استفاده کن. **هیچ مسیر یا نام جدیدی "
                "که در متن کاربر نیست اختراع نکن**. اگر کاربر گفت "
                "`backend/app/services/X/Y.py`، تو همان مسیر را بنویس — نه "
                "`backend/Y.py` و نه `app/services/Z/Y.py`. consistency حیاتی است."
            )

        plan_prompt = f"""تو یک پلانر دقیق هستی. درخواست طولانی کاربر را به مراحل کوچک‌تر و **مستقل** تقسیم می‌کنی.

## قانون‌های حیاتی (دقیقاً رعایت کن):
1. هر مرحله یک **scope مشخص** و **یک action اصلی** دارد (مثل «اضافه کردن endpoint X»، «اصلاح UI Y»، «نوشتن تست Z»، «integration A با B»).
2. مراحل را به ترتیب منطقی پیاده‌سازی مرتب کن (foundation → core → integration → UI → tests → audit).
3. **بدون خلاصه‌سازی و بدون فشرده‌سازی**: اگر کاربر ۸ کار جداگانه را خواسته، **۸ مرحله** بده — نه ۴ مرحلهٔ ادغام‌شده. هدف: **هیچ requirement کاربر گم نشود**.
4. **هیچ سقفی روی تعداد مراحل نیست — حداکثر ۲۰۰ مرحله ولی به این محدودیت نرس مگر واقعاً کاربر بخواهد**. اگر کاربر صراحتاً موارد بیشتری شمارش کرده (مثلاً ۵۰ فاز یا ۸ Bug + ۵ Phase + ۲۰ Stage)، **همه را** بساز. هرگز خلاصه نکن یا بخش‌ها را با هم ادغام نکن. اگر متن کاربر شامل ۴۰ بخش صریح بود، خروجی شامل **دقیقاً ۴۰ مرحله** باشد — نه ۳۰، نه ۳۵.
5. **`raw_excerpt`**: بخش‌هایی از متن کاربر که به این مرحله مربوط است — **verbatim و کامل**، با URLs و نام‌ها. حداقل ۱۰۰ کاراکتر اگر متن کاربر اجازه دهد.
6. **`scope`**: حداقل ۲-۳ جمله — چه چیزی شامل این مرحله است، چه چیزی خارج از این مرحله است، چه نکته‌ای حیاتی است. **نه یک جمله سرسری**.
7. **`key_terms`**: همهٔ نام‌ها (فایل، endpoint، function، URL، library، dataclass، table، …) که کاربر در این بخش گفته. حداقل ۳ آیتم اگر در متن وجود دارد.
8. اگر درخواست کاربر فقط یک کار است (نه چندتایی)، فقط ۱ مرحله بده — ولی همان ۱ مرحله را خیلی غنی توضیح بده.

## مهم: اگر کاربر صراحتاً موارد ۱، ۲، ۳، … را شماره‌گذاری کرده، **برای هر کدام یک مرحله** بساز. اگر بنویسد «و این، و آن، و فلان»، هر کدام جداگانه.

## 🆕 (bug 30 v4) قواعد سخت برای جلوگیری از خطاهای پرتکرار:
- **هرگز** بخش‌هایی که کاربر گفته «قبلاً اجرا شده» یا «مرور» یا «(done)» یا «برای مرجع» را به‌عنوان step اجرایی نساز. این‌ها فقط زمینه هستن.
- اگر یک بخش شامل لیست explicit با شمارهٔ ≥۳ آیتم است (مثل «Chunk ۱..۸»، «گپ ۱..۶»، «۱۲ AC شماره‌دار»، «۱۱ edge case»)، **هر آیتم را یک step مستقل کن** — نه ادغام در یک step خلاصه.
- اگر کاربر جدول AC با ستون‌های (#, AC, identifier) داد، آن جدول را به یک step «meta-test/checklist» تبدیل کن و **همهٔ سطرها را verbatim در `raw_excerpt` کپی کن** — هیچ‌کدام را حذف نکن.
- consistency مسیر فایل: اگر کاربر یک فایل را با مسیر `X/Y/Z.py` گفت، تو دقیقاً همان مسیر را بنویس — نه مسیر متفاوت در stepهای مختلف.{_section_hint}{_id_hint}

## هدف اصلی پروژه:
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

## درخواست کاربر:
\"\"\"
{idea.strip()}
\"\"\"

## خروجی فقط JSON خالص (بدون ``` و توضیح اضافه):

{{
  "steps": [
    {{
      "id": 1,
      "title": "عنوان کوتاه مرحله (یک جمله)",
      "scope": "scope کامل این مرحله — چه چیزی باید انجام شود، چه چیزی خارج از این مرحله است، نکات حیاتی (حداقل ۲-۳ جمله، می‌تواند تا ۱۰۰۰ کاراکتر باشد)",
      "raw_excerpt": "بخش‌هایی از متن کاربر که به این مرحله مربوط است — کلمه به کلمه با URL ها و نام‌ها، حداقل ۱۰۰ char اگر متن طولانی است",
      "key_terms": ["نام فایل ۱", "endpoint ۲", "library ۳", "https://..."],
      "behavior_observable": "رفتار قابل مشاهده پس از این مرحله — چه چیزی کاربر می‌بیند یا چه خروجی observable تولید می‌شود (نه نام فایل، بلکه رفتار).",
      "verification_hint": "کجا verify باید این رفتار را ببیند — مثل /route مشخص، endpoint، یا outcome data",
      "business_intent": "چرا این مرحله لازم است — هدف کسب‌وکاری یا کاربر",
      "non_goals": "چه چیزی این مرحله نیست — جلوگیری از scope creep"
    }}
  ],
  "rationale": "چرا این تقسیم منطقی است (۲-۳ جمله)"
}}

## 🎯 معیار رفتاری (R9 + R13 — مهم برای جلوگیری از false-positive):
- هر AC که نام فایل/کلاس می‌برد، در `behavior_observable` رفتار همان feature را به‌صورت **observable** بنویس.
  - ❌ بد: «فایل XyzPanel.tsx بساز»
  - ✅ خوب: «پنلی که watched projects را list می‌کند — می‌تواند در app/X/page.tsx یا کامپوننت جدا»
- `verification_hint` کمک می‌کند verify بداند کجا feature را بجوید — URL یا event مشخص.
- `business_intent` کاربر را کمک می‌کند بفهمد چرا این مرحله مهم است.
- اگر مرحله **vague** است (مثل "system works")، آن را به sub-behaviors **concrete** split کن.
- `non_goals` باید **صریح** باشد تا verify فریب نخورد.
"""
        # 🆕 (bug 30) — برای ایده‌های با چند بخش صریح، max_tokens را بالا ببر
        # تا output truncate نشود. DeepSeek-Chat تا ۱۶۳۸۴ توکن خروجی می‌دهد.
        # 🆕 (bug 30 v3) — برای متون خیلی بلند (>15 section)، حتی 16k کافی نیست —
        # ولی نمی‌توان از limit مدل بالاتر رفت. در آن حالت، programmatic
        # chunking fallback خودکار فعال می‌شود (هر chunk جدا AI call می‌خورد).
        _max_out_tokens = 16000 if _is_multi_section else 12000

        async def _run_planner(_prompt: str, _budget: int) -> List[Dict[str, Any]]:
            """یک تلاش پلانر — اجرای AI، parse JSON، normalize steps."""
            response = await self._ai_generate(
                _prompt,
                model_id=(model_ids[0] if model_ids else model_id),
                max_tokens=_budget,
                temperature=0.2,
            )
            parsed = self._extract_json(response)
            if not isinstance(parsed, dict):
                return []
            raw_steps = parsed.get("steps") or []
            if not isinstance(raw_steps, list):
                return []
            out: List[Dict[str, Any]] = []
            for i, s in enumerate(raw_steps):
                if not isinstance(s, dict):
                    continue
                title = (s.get("title") or "").strip()
                scope = (s.get("scope") or "").strip()
                if not title or not scope:
                    continue
                out.append({
                    "id": int(s.get("id") or (i + 1)),
                    "title": title[:300],  # 🔴 v1: 200→300
                    # 🔴 v2: 20000→5000 — 20K per-step خیلی زیاد بود برای
                    # output budget. step planner 64K خروجی داره؛ با
                    # 50 step × 70K (scope+excerpt) = 3.5MB → overflow.
                    # 5K scope + 15K excerpt = 20K/step × 50 step = 1MB
                    # هنوز بیش از budget، ولی AI خودش انتخاب می‌کنه چقدر
                    # بنویسه (cap فقط max-allowed است، نه instruction).
                    "scope": scope[:5000],
                    "raw_excerpt": (s.get("raw_excerpt") or "").strip()[:15000],
                    "key_terms": [str(k) for k in (s.get("key_terms") or [])[:50]],
                    "behavior_observable": str(s.get("behavior_observable") or "").strip()[:2000],
                    "verification_hint": str(s.get("verification_hint") or "").strip()[:1000],
                    "business_intent": str(s.get("business_intent") or "").strip()[:300],
                    "non_goals": str(s.get("non_goals") or "").strip()[:300],
                })
            # 🆕 (bug 30 v3) — cap بالا برده شد به ۲۰۰ (قبلاً ۳۰ بود).
            # برای متن‌های طولانی با چند Phase + Bug + Stage تو در تو، باید
            # همه مراحل حفظ شوند.
            return out[:200]

        # 🆕 (bug 30 v2) — Programmatic chunking fallback
        # تابع کمکی: idea را با موقعیت header های detected به chunks تقسیم می‌کند
        # هر chunk = یک بخش از header شروع تا header بعدی (یا انتها)
        def _split_idea_by_sections() -> List[Tuple[str, str]]:
            """خروجی: [(header, chunk_text), ...]"""
            if not _section_starts:
                return []
            chunks: List[Tuple[str, str]] = []
            for idx, (offset, header) in enumerate(_section_starts):
                next_off = (
                    _section_starts[idx + 1][0]
                    if idx + 1 < len(_section_starts)
                    else len(idea)
                )
                chunk_text = idea[offset:next_off].strip()
                # حذف chunk های خیلی کوچک (احتمالاً false-positive section)
                if len(chunk_text) >= 200:
                    chunks.append((header, chunk_text))
            return chunks

        async def _plan_single_section(
            header: str, section_text: str, section_idx: int,
        ) -> Optional[Dict[str, Any]]:
            """یک AI call برای یک بخش — یک step تولید می‌کند."""
            # 🆕 (bug 30 v4) — identifier hint مختصر برای chunking نیز
            _mini_id_lines: List[str] = []
            if _extracted_ids["paths"]:
                _mini_id_lines.append(
                    "📂 مسیرهای فایل (از این لیست استفاده کن، اختراع نکن): "
                    + ", ".join(_extracted_ids["paths"][:12])
                )
            if _extracted_ids["classes"]:
                _mini_id_lines.append(
                    "🏷 کلاس‌های ذکرشده: "
                    + ", ".join(_extracted_ids["classes"][:12])
                )
            _mini_id_hint = "\n\n" + "\n".join(_mini_id_lines) if _mini_id_lines else ""

            mini_prompt = f"""تو یک پلانر دقیق هستی. این **یک بخش** از یک درخواست بزرگ‌تر است. وظیفه‌ات: این بخش را به **یک مرحله** اجرایی تبدیل کن.

## هدف پروژه:
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

## این بخش از درخواست کاربر (header: {header}):
\"\"\"
{section_text}
\"\"\"

## قواعد سخت:
- اگر این بخش صراحتاً می‌گوید «قبلاً اجرا شده» یا «مرور» یا «(done)» یا «برای مرجع»، خروجی را `{{"skip": true, "reason": "..."}}` بده — هیچ step نساز.
- اگر بخش شامل لیست شماره‌دار با ≥۳ آیتم explicit است، در `scope` این موضوع را ذکر کن و در `raw_excerpt` همه آیتم‌ها را verbatim بگذار.
- نام فایل/کلاس را عیناً از متن استفاده کن — اختراع نکن.{_mini_id_hint}

## خروجی فقط JSON خالص (یک object، نه array):
{{
  "title": "عنوان کوتاه این بخش (یک جمله — بر اساس header اگر مرتبط است)",
  "scope": "scope کامل این بخش — چه چیزی شامل است، چه چیزی خارج، نکات حیاتی (۲-۵ جمله)",
  "raw_excerpt": "بخش‌هایی از متن کاربر مربوط به این بخش — verbatim، با URLها و نام‌ها (تا ۱۲۰۰ کاراکتر)",
  "key_terms": ["نام‌های فایل/endpoint/library/متغیر/کلاس که در این بخش آمده"],
  "behavior_observable": "رفتار قابل مشاهده پس از این مرحله",
  "verification_hint": "کجا verify باید این رفتار را ببیند (URL/endpoint/outcome)",
  "business_intent": "چرا این مرحله لازم است",
  "non_goals": "چه چیزی این مرحله نیست"
}}
"""
            try:
                _resp = await self._ai_generate(
                    mini_prompt,
                    model_id=(model_ids[0] if model_ids else model_id),
                    max_tokens=2500,
                    temperature=0.2,
                )
                _parsed = self._extract_json(_resp)
                if not isinstance(_parsed, dict):
                    return None
                # 🆕 (bug 30 v4) — اگر AI تشخیص داد این section reference است
                if _parsed.get("skip") is True:
                    logger.info(
                        f"_plan_single_section[{section_idx}]: AI marked as "
                        f"reference/skip (reason: {_parsed.get('reason', 'n/a')})"
                    )
                    return None
                title = (_parsed.get("title") or "").strip()
                scope = (_parsed.get("scope") or "").strip()
                if not title or not scope:
                    return None
                return {
                    "id": section_idx + 1,
                    "title": title[:300],
                    # 🔴 v3 (code-review-followup): همهٔ caps با builder بالا یکسان شد.
                    # قبلاً behavior_observable[:500] و verification_hint[:300] بود
                    # (مقادیر pre-v1) ولی builder بالا [:2000] و [:1000] داره.
                    # divergence که از v1 جا مونده بود.
                    "scope": scope[:5000],
                    "raw_excerpt": (_parsed.get("raw_excerpt") or "").strip()[:15000],
                    "key_terms": [str(k) for k in (_parsed.get("key_terms") or [])[:50]],
                    "behavior_observable": str(_parsed.get("behavior_observable") or "").strip()[:2000],
                    "verification_hint": str(_parsed.get("verification_hint") or "").strip()[:1000],
                    "business_intent": str(_parsed.get("business_intent") or "").strip()[:300],
                    "non_goals": str(_parsed.get("non_goals") or "").strip()[:300],
                }
            except Exception as _e:
                logger.warning(f"_plan_single_section[{section_idx}] failed: {_e}")
                return None

        # 🆕 (bug 30 v4) — Post-processing: path consistency + dedup.
        # هر step ممکن است در `scope` یا `key_terms` مسیر فایل ذکر کند.
        # اگر دو step به فایل مشابه (basename یکسان) اشاره می‌کنند ولی مسیر
        # متفاوت، آن‌ها را به مسیر اول هماهنگ می‌کنیم. همچنین stepهای با
        # عنوان تقریباً یکسان (Jaccard >= 0.7) را merge می‌کنیم.
        def _normalize_paths_across_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            # نقشه basename -> اولین مسیر کاملی که دیده شده
            canonical: Dict[str, str] = {}
            _path_re = _re_seg.compile(
                r'\b((?:backend|frontend|docs|tests|src|app|scripts)/[\w/\.\-]+\.(?:py|tsx?|jsx?|md|json|yaml|yml|sh|toml))\b'
            )
            # pass 1: collect canonical
            for st in steps:
                for fld in ("scope", "raw_excerpt", "title"):
                    txt = st.get(fld) or ""
                    for _m in _path_re.finditer(txt):
                        _p = _m.group(1)
                        _base = _p.rsplit("/", 1)[-1]
                        canonical.setdefault(_base, _p)
                for kt in st.get("key_terms") or []:
                    if isinstance(kt, str) and "/" in kt and "." in kt:
                        _base = kt.rsplit("/", 1)[-1]
                        if _base.split(".")[-1] in ("py", "tsx", "ts", "jsx", "js", "md", "json", "yaml", "yml", "sh", "toml"):
                            canonical.setdefault(_base, kt)
            # pass 2: replace alternative paths with canonical
            _replacements = 0
            for st in steps:
                for fld in ("scope", "raw_excerpt", "title"):
                    txt = st.get(fld) or ""
                    new_txt = txt
                    for _m in _path_re.finditer(txt):
                        _p = _m.group(1)
                        _base = _p.rsplit("/", 1)[-1]
                        canon = canonical.get(_base)
                        if canon and canon != _p:
                            new_txt = new_txt.replace(_p, canon)
                            _replacements += 1
                    if new_txt != txt:
                        st[fld] = new_txt
                # نرمالیزه کردن key_terms
                _new_kt: List[str] = []
                for kt in st.get("key_terms") or []:
                    if isinstance(kt, str) and "/" in kt and "." in kt:
                        _base = kt.rsplit("/", 1)[-1]
                        canon = canonical.get(_base)
                        if canon and canon != kt:
                            _new_kt.append(canon)
                            _replacements += 1
                            continue
                    _new_kt.append(kt)
                st["key_terms"] = _new_kt
            if _replacements > 0:
                logger.info(
                    f"_ai_plan_steps: normalized {_replacements} inconsistent "
                    f"file paths across steps (canonicalized to first-seen form)"
                )
            return steps

        def _dedup_similar_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """دو step با similarity ≥0.75 در عنوان merge می‌شوند (دومی drop)."""
            if len(steps) < 2:
                return steps

            def _tokenize(s: str) -> set:
                s = _re_seg.sub(r'[^\w؀-ۿ\s]', ' ', (s or "").lower())
                return {t for t in s.split() if len(t) > 2}

            def _jaccard(a: set, b: set) -> float:
                if not a or not b:
                    return 0.0
                return len(a & b) / len(a | b)

            kept: List[Dict[str, Any]] = []
            kept_tokens: List[set] = []
            _merged = 0
            for st in steps:
                _t = _tokenize(st.get("title", ""))
                _is_dup = False
                for _i, _kt in enumerate(kept_tokens):
                    if _jaccard(_t, _kt) >= 0.75:
                        # merge: scope/key_terms از step دوم به اول اضافه می‌شود
                        kept[_i]["scope"] = (
                            kept[_i].get("scope", "")
                            + "\n— [merged] "
                            + (st.get("scope") or "")
                        )[:2500]
                        _kt_combined = list({
                            *(kept[_i].get("key_terms") or []),
                            *(st.get("key_terms") or []),
                        })
                        kept[_i]["key_terms"] = _kt_combined[:25]
                        _is_dup = True
                        _merged += 1
                        break
                if not _is_dup:
                    kept.append(st)
                    kept_tokens.append(_t)
            if _merged > 0:
                logger.info(
                    f"_ai_plan_steps: merged {_merged} near-duplicate steps "
                    f"(title Jaccard >= 0.75)"
                )
            # renumber ids
            for _i, st in enumerate(kept, start=1):
                st["id"] = _i
            return kept

        def _post_process(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            if not steps:
                return steps
            steps = _normalize_paths_across_steps(steps)
            steps = _dedup_similar_steps(steps)
            return steps

        try:
            valid_steps = await _run_planner(plan_prompt, _max_out_tokens)
            valid_steps = _post_process(valid_steps)

            # 🆕 (bug 30) — اگر بخش‌بندی صریح زیاد بود ولی خروجی خیلی کمتر،
            # AI خلاصه کرده — یک‌بار دیگر با تأکید صریح‌تر تلاش کن.
            if (
                _is_multi_section
                and _section_count >= 3
                and len(valid_steps) < max(3, int(_section_count * 0.5))
            ):
                logger.warning(
                    f"_ai_plan_steps: AI returned {len(valid_steps)} steps but "
                    f"idea has {_section_count} explicit sections — retrying with stricter prompt"
                )
                retry_hint = (
                    f"\n\n🚨🚨🚨 **بازنگری اجباری**: تلاش قبلی فقط "
                    f"{len(valid_steps)} مرحله ساخت در حالی که متن دارای "
                    f"{_section_count} بخش صریح شماره‌دار است. **این بار "
                    f"دقیقاً {min(_section_count, 200)} مرحله بساز** — برای "
                    f"هر بخش یک مرحله. هر چیزی کمتر = خلاصه‌سازی = اشتباه."
                )
                retry_prompt = plan_prompt + retry_hint
                retry_steps = await _run_planner(retry_prompt, _max_out_tokens)
                retry_steps = _post_process(retry_steps)
                if len(retry_steps) > len(valid_steps):
                    logger.info(
                        f"_ai_plan_steps: retry succeeded — "
                        f"{len(valid_steps)} → {len(retry_steps)} steps"
                    )
                    valid_steps = retry_steps

            # 🆕 (bug 30 v2) — اگر هنوز بعد از retry تعداد مراحل خیلی کمتر از
            # سکشن‌های detected است، به chunking برنامه‌ای سوئیچ کن.
            # هر section به یک AI call تبدیل می‌شود (parallel) — این روش
            # AI را مجبور می‌کند نتواند خلاصه کند چون هر call فقط ۱ بخش می‌بیند.
            if (
                _is_multi_section
                and _section_count >= 5
                and len(valid_steps) < max(5, int(_section_count * 0.6))
            ):
                logger.warning(
                    f"_ai_plan_steps: retry still insufficient ({len(valid_steps)}/"
                    f"{_section_count}) — switching to programmatic chunking"
                )
                _chunks = _split_idea_by_sections()
                # 🆕 (bug 30 v3) — cap بالا برده شد به ۲۰۰
                _chunks = _chunks[:200]  # cap سخت
                logger.info(
                    f"_ai_plan_steps: chunking → {len(_chunks)} chunks "
                    f"(parallel AI calls)"
                )
                import asyncio as _aio
                _tasks = [
                    _plan_single_section(_h, _txt, _i)
                    for _i, (_h, _txt) in enumerate(_chunks)
                ]
                _results = await _aio.gather(*_tasks, return_exceptions=False)
                _chunk_steps = [r for r in _results if r is not None]
                _chunk_steps = _post_process(_chunk_steps)
                if len(_chunk_steps) > len(valid_steps):
                    logger.info(
                        f"_ai_plan_steps: chunking produced {len(_chunk_steps)} "
                        f"steps (vs {len(valid_steps)} from monolithic planner)"
                    )
                    valid_steps = _chunk_steps

            return valid_steps
        except Exception as e:
            logger.warning(f"_ai_plan_steps_from_idea failed: {e}")
            return []

    async def _idea_to_prompt_multi_pass(
        self,
        idea: str,
        watched_id: Optional[str],
        type_: str = "other",
        priority: str = "medium",
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Multi-pass prompt generation:
          Pass 1: AI ایده را به ۱-۶ مرحله می‌شکند
          Pass 2..N: برای هر مرحله یک sub-prompt غنی می‌سازد (با همان منطق
                     idea_to_prompt ولی scope محدود)
          Pass N+1: همهٔ sub-prompts را به یک پرامپت master ادغام می‌کند

        مزیت: برای مدل‌های کم‌قدرت، هر pass scope کوچک‌تری دارد → کیفیت بسیار بهتر.

        خروجی همان format `idea_to_prompt` است (title, prompt, target_files, …)
        یا None اگر multi-pass نتوانست انجام شود.
        """
        from .oversight_strong_prompt import EXECUTOR_DISCLAIMER, build_strong_prompt

        watched = self._find_watched(watched_id) if watched_id else None
        user_goal = (watched.user_notes or "").strip() if watched else ""

        # Pass 1: تقسیم به مراحل
        logger.info("idea_to_prompt multi-pass: Pass 1 — splitting into steps")
        steps = await self._ai_plan_steps_from_idea(idea, user_goal, model_id, model_ids)
        if not steps:
            logger.info("multi-pass: AI نتوانست تقسیم کند → fallback به single-pass")
            return None
        # 🛡 (audit fix #3) — حتی اگر فقط 1 مرحله بود، multi-pass را
        # ادامه می‌دهیم تا چک‌لیست (هرچند با ۱ آیتم) تولید شود. کاربر
        # حداقل یک checkbox برای پیگیری دارد، و verify می‌تواند آن را
        # تیک بزند.
        if len(steps) < 1:
            logger.info("multi-pass: 0 مرحله — fallback به single-pass")
            return None
        if len(steps) == 1:
            logger.info("multi-pass: فقط ۱ مرحله — همچنان adامه می‌دهیم تا checklist تولید شود")

        logger.info(f"multi-pass: {len(steps)} مرحله شناسایی شد")

        # Pass 2..N: برای هر مرحله، single-pass idea_to_prompt با scope محدود
        # 🆕 PARALLEL execution — کاهش زمان از O(N × 30s) به O(30s) برای N step
        import asyncio as _asyncio

        async def _generate_for_step(step: Dict[str, Any]) -> Dict[str, Any]:
            """نسل sub-prompt برای یک مرحله — fail-safe (fallback به placeholder)."""
            mini_idea = (
                f"{step['title']}\n\n"
                f"{step['scope']}\n\n"
                f"--- بخش مربوط از درخواست اصلی کاربر ---\n"
                f"{step['raw_excerpt']}\n\n"
                f"--- کلیدواژه‌ها ---\n"
                f"{', '.join(step['key_terms']) if step['key_terms'] else '(ندارد)'}"
            )
            logger.info(f"multi-pass: Pass {step['id']} — «{step['title'][:60]}»")
            try:
                sub = await self._idea_to_prompt_single_pass(
                    idea=mini_idea,
                    watched_id=watched_id,
                    type_=type_,
                    priority=priority,
                    model_id=model_id,
                    model_ids=model_ids,
                )
                return {"step": step, "result": sub}
            except Exception as se:
                logger.warning(f"multi-pass: step {step['id']} failed: {se}")
                return {
                    "step": step,
                    "result": {
                        "title": step["title"],
                        "prompt": (
                            f"## هدف\n{step['scope']}\n\n"
                            f"## بخش مربوط از متن کاربر\n```\n{step['raw_excerpt']}\n```\n\n"
                            f"## معیار پذیرش\n- پیاده‌سازی موفق این مرحله"
                        ),
                        "target_files": [],
                        "target_locations": [],
                        "related_files": [],
                        "acceptance_criteria": [],
                    },
                }

        # موازی اجرا — تا 6 step هم در ~30s تمام شوند (نه 3 دقیقه)
        # return_exceptions=True برای ایمنی: حتی اگر یک step به‌طور غیرمنتظره
        # exception throw کرد، بقیه ادامه می‌دهند.
        gathered = await _asyncio.gather(
            *[_generate_for_step(step) for step in steps],
            return_exceptions=True,
        )
        # فیلتر valid + placeholder برای exception ها
        sub_results = []
        for i, r in enumerate(gathered):
            if isinstance(r, Exception):
                step = steps[i]
                logger.warning(f"multi-pass: step {step['id']} raised: {r}")
                sub_results.append({
                    "step": step,
                    "result": {
                        "title": step["title"],
                        "prompt": (
                            f"## هدف\n{step['scope']}\n\n"
                            f"## ⚠️ خطا در تولید جزئیات\n`{str(r)[:200]}`\n\n"
                            f"## معیار پذیرش\n- پیاده‌سازی موفق این مرحله"
                        ),
                        "target_files": [],
                        "target_locations": [],
                        "related_files": [],
                        "acceptance_criteria": [],
                    },
                })
            elif isinstance(r, dict):
                sub_results.append(r)
        # حفظ ترتیب بر اساس step.id
        sub_results.sort(key=lambda r: r["step"]["id"])

        if not sub_results:
            return None

        # Pass N+1: Merge همهٔ sub-prompts به یک master prompt
        logger.info(f"multi-pass: Pass {len(steps) + 1} — merging {len(sub_results)} sub-prompts")
        master_title = (idea.strip().split("\n")[0])[:80] + (f" ({len(steps)} مرحله)" if len(steps) > 1 else "")

        merged_parts: List[str] = []
        merged_parts.append(EXECUTOR_DISCLAIMER)
        merged_parts.append("")
        merged_parts.append("---")
        merged_parts.append("")

        # متن خام کاربر (verbatim)
        merged_parts.append(
            "## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)\n"
            "_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند.)_\n\n"
            "```\n"
            f"{idea.strip()}\n"
            "```"
        )
        merged_parts.append("")

        # 🆕 چک‌لیست مراحل (verify خودکار این را به‌روز می‌کند)
        merged_parts.append(
            f"## 📋 چک‌لیست مراحل ({len(steps)} مرحله)\n\n"
            "این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله "
            "به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**\n"
            "وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.\n"
        )
        for s in steps:
            merged_parts.append(f"- [ ] **مرحله {s['id']}: {s['title']}** — {s['scope'][:300]}")

        # عناصر متادیتای ادغام‌شده
        all_target_files: List[str] = []
        all_target_locations: List[Dict[str, Any]] = []
        all_related: List[Dict[str, Any]] = []
        all_ac: List[str] = []

        # برای هر مرحله، بخش جداگانه
        for sr in sub_results:
            step = sr["step"]
            sub = sr["result"]
            merged_parts.append("")
            merged_parts.append("---")
            merged_parts.append("")
            merged_parts.append(f"# 🔹 مرحله {step['id']}: {step['title']}")
            merged_parts.append("")
            merged_parts.append(f"**Scope:** {step['scope']}")
            if step["key_terms"]:
                merged_parts.append(f"**Key terms:** {', '.join(step['key_terms'])}")
            if step.get("raw_excerpt"):
                merged_parts.append("")
                merged_parts.append("**بخش مربوط از متن کاربر:**")
                merged_parts.append("```")
                merged_parts.append(step["raw_excerpt"])
                merged_parts.append("```")
            merged_parts.append("")
            # محتوای sub prompt — حذف disclaimer تکراری و verbatim تکراری
            sub_prompt_clean = self._strip_disclaimer_and_verbatim(sub.get("prompt") or "")
            merged_parts.append(sub_prompt_clean)

            # جمع‌آوری meta
            for tf in (sub.get("target_files") or []):
                if tf and tf not in all_target_files:
                    all_target_files.append(tf)
            for tl in (sub.get("target_locations") or []):
                if isinstance(tl, dict):
                    all_target_locations.append(tl)
            for rf in (sub.get("related_files") or []):
                if isinstance(rf, dict):
                    all_related.append(rf)
            for a in (sub.get("acceptance_criteria") or []):
                if a and a not in all_ac:
                    all_ac.append(a)

        # AC کلی نهایی
        merged_parts.append("")
        merged_parts.append("---")
        merged_parts.append("")
        merged_parts.append("## ✅ معیارهای پذیرش کلی (همهٔ مراحل)")
        if all_ac:
            for a in all_ac[:20]:
                merged_parts.append(f"- [ ] {a}")
        else:
            merged_parts.append("- [ ] همهٔ مراحل بالا با موفقیت پیاده‌سازی شده‌اند")
            merged_parts.append("- [ ] تست‌های موجود pass می‌شوند")
            merged_parts.append("- [ ] هیچ regression رخ نداده")

        master_prompt = "\n".join(merged_parts)

        # 🆕 بزرگ‌ترین تعداد فایل‌های deep-read در sub-pass ها (هر pass
        # تقریباً همان مجموعه را می‌خواند، پس max نماینده‌ی خوبی است)
        _mp_deep_count = max(
            (
                (sr.get("result") or {}).get("deep_files_count", 0)
                for sr in sub_results if isinstance(sr, dict)
            ),
            default=0,
        )

        return {
            "title": master_title,
            "prompt": master_prompt,
            "target_files": all_target_files,
            "target_locations": all_target_locations,
            "related_files": all_related,
            "acceptance_criteria": all_ac,
            "type": type_,
            "priority": priority,
            "estimate": "large" if len(steps) >= 4 else "medium",
            "raw_response": f"[multi-pass with {len(steps)} steps]",
            "_multi_pass": True,
            "_step_count": len(steps),
            "deep_files_count": _mp_deep_count,
            # 🆕 (Telegram raw_idea bug fix #2) — مسیر multi-pass هم raw_idea
            # را برگرداند تا callers (notification_service compose) از آن
            # به‌جای fallback "(از فایل پیوست)" استفاده کنند. این idea شامل
            # placeholder + متن augmented از فایل‌های پیوست است (که
            # _resolve_attachments_for_idea در idea_to_prompt اضافه کرده).
            "raw_idea": idea,
            # 🆕 چک‌لیست مراحل برای ذخیره در OversightTask.task_steps
            "task_steps": [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "scope": s["scope"],
                    "raw_excerpt": s.get("raw_excerpt", ""),
                    "key_terms": s.get("key_terms", []),
                    "status": "pending",  # pending|done|partial|not_done|error
                    "completion_pct": 0,
                    "remaining": "",
                    "evidence": "",
                    "last_verified_at": None,
                    "completed_at": None,
                }
                for s in steps
            ],
            "overall_completion_pct": 0,
        }

    @staticmethod
    def _strip_disclaimer_and_verbatim(prompt_text: str) -> str:
        """حذف DISCLAIMER و بخش verbatim از یک sub-prompt برای ادغام بدون تکرار."""
        if not prompt_text:
            return ""
        text = prompt_text
        # حذف DISCLAIMER اگر در ابتدا هست
        try:
            from .oversight_strong_prompt import EXECUTOR_DISCLAIMER
            if text.startswith(EXECUTOR_DISCLAIMER):
                text = text[len(EXECUTOR_DISCLAIMER):].lstrip()
            # حذف "---\n\n"
            if text.startswith("---"):
                idx = text.find("\n", 3)
                if idx > 0:
                    text = text[idx:].lstrip()
        except Exception:
            pass
        # حذف "## 📥 درخواست خام کاربر..." و کل بلوک code fence آن
        import re as _re
        verbatim_pattern = _re.compile(
            r'##\s*📥\s*درخواست خام کاربر.*?```\s*\n.*?\n```',
            _re.DOTALL,
        )
        text = verbatim_pattern.sub("", text).strip()
        return text

    async def _idea_to_prompt_single_pass(
        self,
        idea: str,
        watched_id: Optional[str],
        type_: str = "other",
        priority: str = "medium",
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """invocation single-pass بدون چک complex (برای استفاده داخل multi-pass).

        برای جلوگیری از infinite recursion، parameter `_skip_multi_pass=True`
        به idea_to_prompt پاس می‌شود (نه instance attribute — تا concurrency-safe باشد).
        """
        return await self.idea_to_prompt(
            idea=idea, watched_id=watched_id, type_=type_,
            priority=priority, model_id=model_id, model_ids=model_ids,
            _skip_multi_pass=True,
        )

    async def _resolve_attachments_for_idea(
        self,
        idea: str,
        upload_session_ids: List[str],
        *,
        progress_track_id: Optional[str] = None,
    ) -> "Tuple[str, List[Dict[str, Any]]]":
        """فایل‌های پیوست را به متن استخراج‌شده تبدیل می‌کند و به idea append.

        - برای هر session_id، اگر extraction انجام نشده، آن را trigger می‌کند
          (با auto_temp_activate اگر مدل enabled نباشد).
        - متن کامل هر فایل به‌ترتیب file_order ASC append می‌شود.
        - sentinel `## 📎 فایل پیوست #N: {filename} (mime, model)` بین فایل‌ها.

        خروجی: (augmented_idea, attachments_meta)
        attachments_meta: [{session_id, file_order, filename, mime, extraction_id,
                            total_segments, status, char_count, model_used, error}]

        🛡 (audit fix CRITICAL) — اگر فایل غیرمتنی (image/video/audio) هست
        ولی هیچ مدل بصری با API key فعال نیست، یک ValueError با اطلاعات
        کامل candidates می‌اندازد تا caller بتواند modal toggle نشان دهد.
        """
        from .oversight_upload_session import get_upload_session_service
        from .oversight_extraction import (
            extract_session, get_extraction_repo,
        )
        from .oversight_model_temp_activate import check_extraction_model_availability
        upload_svc = get_upload_session_service()
        repo = get_extraction_repo()

        # رزولو sessions + sort by file_order
        sessions = []
        for sid in upload_session_ids:
            s = upload_svc.get(sid)
            if s is None:
                logger.warning(f"upload session not found: {sid}")
                continue
            sessions.append(s)
        sessions.sort(key=lambda s: s.file_order)

        # 🛡 (audit fix CRITICAL) — قبل از شروع extraction، چک کن آیا
        # **همهٔ** sessionهای غیرمتنی یک مدل بصری معتبر (با API key) موجود
        # دارند. اگر نه، یک ValueError با ساختار blocked_no_vision_model
        # می‌اندازیم تا API route بتواند 409 با candidates برگرداند → frontend
        # modal نشان می‌دهد.
        missing_vision_for: List[Dict[str, Any]] = []
        # 🛡 (audit fix) — لیست extensionهای کد و آرشیو که vision نیاز ندارند
        # (extraction آن‌ها به‌صورت text/structured صورت می‌گیرد)
        _no_vision_text_mimes = {
            "application/json", "application/xml", "application/yaml",
            "application/x-yaml", "application/toml", "application/x-toml",
            "application/x-ndjson",
            # archives — extracted to inner text files
            "application/zip", "application/x-tar", "application/gzip",
            "application/x-7z-compressed", "application/x-zip-compressed",
            # ipynb — JSON parsed
            "application/x-ipynb+json",
        }
        _no_vision_extensions = (
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp",
            ".h", ".hpp", ".go", ".rs", ".rb", ".php", ".html", ".htm",
            ".css", ".scss", ".sql", ".sh", ".bash", ".ps1", ".kt",
            ".swift", ".dart", ".r", ".lua", ".pl", ".scala", ".clj",
            ".ex", ".exs", ".elm", ".vue", ".cs",
            # archives + ipynb (by extension fallback)
            ".zip", ".tar", ".gz", ".7z", ".ipynb",
            # text-like
            ".md", ".markdown", ".txt", ".csv", ".tsv", ".log", ".ini",
            ".yml", ".yaml", ".toml", ".json", ".xml",
        )
        for s in sessions:
            mt = (s.mime_type or "").lower()
            fname_lower = (s.original_filename or "").lower()
            # 🛡 text/code/archive/ipynb — vision نیاز ندارند
            if mt.startswith("text/") or mt in _no_vision_text_mimes:
                continue
            # 🛡 extension fallback — برای application/octet-stream یا mime عمومی
            if any(fname_lower.endswith(ext) for ext in _no_vision_extensions):
                continue
            avail = check_extraction_model_availability(mt)
            if not avail.get("available"):
                missing_vision_for.append({
                    "session_id": s.id,
                    "filename": s.original_filename,
                    "mime_type": s.mime_type,
                    "file_order": s.file_order,
                    "candidates": avail.get("candidates") or [],
                })
        if missing_vision_for:
            # یک خطای structured بساز — API route آن را به 409 تبدیل می‌کند
            err = ValueError("blocked_no_vision_model")
            err.blocked_payload = {  # type: ignore[attr-defined]
                "error": "blocked_no_vision_model",
                "message": (
                    "برای استخراج فایل‌های بصری/صوتی، یک مدل multimodal با "
                    "API key معتبر باید فعال باشد. لطفاً Gemini یا مدل "
                    "مشابه را در /models فعال کن و کلید API را در env تنظیم کن."
                ),
                "missing_files": missing_vision_for,
                # candidates اول را از اولین file ناتوان برمی‌داریم
                "candidates": missing_vision_for[0].get("candidates", []),
                "mime_type": missing_vision_for[0].get("mime_type"),
            }
            raise err

        attachments_meta: List[Dict[str, Any]] = []
        appended_parts: List[str] = []

        # 🆕 (Stage 6) — progress tracker (اختیاری)
        tracker = None
        if progress_track_id:
            try:
                from .oversight_progress import get_progress_tracker
                tracker = get_progress_tracker()
            except Exception:
                tracker = None

        total_files = len(sessions)
        for idx_file, s in enumerate(sessions, start=1):
            if tracker:
                try:
                    await tracker.update(
                        progress_track_id,
                        stage=f"extracting_file_{idx_file}",
                        current=idx_file - 1,  # هنوز این فایل تمام نشده
                        total=total_files,
                        detail=f"📎 فایل {idx_file}/{total_files}: {s.original_filename[:50]}",
                        throttle_sec=2.0,
                    )
                except Exception:
                    pass
            entry: Dict[str, Any] = {
                "session_id": s.id,
                "file_order": s.file_order,
                "filename": s.original_filename,
                "mime_type": s.mime_type,
                "status": s.status,
            }
            # اگر هنوز upload کامل نشده، skip با warning
            if s.status not in ("completed", "extracting", "extracted"):
                entry["error"] = f"upload not completed (status={s.status})"
                attachments_meta.append(entry)
                appended_parts.append(
                    f"\n\n## 📎 فایل پیوست #{s.file_order}: {s.original_filename}\n"
                    f"⚠️ این فایل هنوز کامل آپلود نشده (status={s.status}) — نادیده گرفته شد.\n"
                )
                continue

            # extraction موجود؟ اگر نه، trigger کن
            existing = repo.list_by_session(s.id)
            fe = existing[0] if existing else None
            if fe is None or fe.status != "extracted":
                try:
                    fe = await extract_session(s.id, user_idea=idea[:2000])
                except Exception as e:
                    entry["error"] = f"extraction failed: {str(e)[:300]}"
                    attachments_meta.append(entry)
                    appended_parts.append(
                        f"\n\n## 📎 فایل پیوست #{s.file_order}: {s.original_filename}\n"
                        f"❌ استخراج با خطا روبه‌رو شد: {str(e)[:200]}\n"
                    )
                    continue

            entry["extraction_id"] = fe.id
            entry["total_segments"] = fe.total_segments
            entry["model_used"] = fe.model_used
            full_text = repo.full_text(fe.id) or fe.full_text_cache or ""
            entry["char_count"] = len(full_text)

            # 🛡 (audit fix CRITICAL) — تشخیص "همهٔ segmentها fail شدند":
            # اگر متن استخراج‌شده فقط شامل placeholderهای خطا (`[خطا: ...]`،
            # `[timeout ...]`) است و هیچ محتوای واقعی استخراج نشده، این فایل
            # نباید به‌عنوان محتوای کاربر به prompt-builder پاس داده شود —
            # وگرنه مدل، خود پیام‌های خطا را به‌عنوان درخواست کاربر تفسیر
            # می‌کند و پرامپت توهمی تولید می‌شود (مثلاً «یک endpoint
            # transcribe بساز» در حالی که کاربر فقط می‌خواست یک ویس بدهد).
            import re as _re_fail
            non_error_text = _re_fail.sub(
                r"\[(?:خطا|timeout)[^\]]*\]",
                "",
                full_text,
            )
            # heading lines (## ...) را هم حذف کن — اگر بدون error placeholder
            # فقط headings باقی بماند یعنی هیچ محتوای واقعی نبوده
            non_error_text = _re_fail.sub(
                r"^##\s+.*$",
                "",
                non_error_text,
                flags=_re_fail.MULTILINE,
            ).strip()
            extraction_all_failed = (
                fe.total_segments > 0
                and len(non_error_text) < 20
                and "[خطا" in full_text
            )
            entry["all_segments_failed"] = extraction_all_failed
            attachments_meta.append(entry)

            if extraction_all_failed:
                # محتوای خراب را به prompt پاس نده — یک پیام صریح خطا قرار بده
                logger.warning(
                    f"resolve_attachments: همهٔ {fe.total_segments} segment فایل "
                    f"#{s.file_order} ({s.original_filename}) با خطا برگشتند "
                    f"— محتوای ناقص به prompt-builder پاس نمی‌شود"
                )
                appended_parts.append(
                    f"\n\n## 📎 فایل پیوست #{s.file_order}: {s.original_filename}\n"
                    f"❌ **استخراج این فایل ناموفق بود** "
                    f"(mime={s.mime_type} • model={fe.model_used} • "
                    f"همهٔ {fe.total_segments} segment با خطا برگشتند).\n\n"
                    f"⚠️ این فایل به‌عنوان محتوای ورودی به مدل تولید پرامپت "
                    f"پاس داده **نمی‌شود** — وگرنه مدل پیام‌های خطا را به‌عنوان "
                    f"درخواست کاربر تفسیر می‌کند. لطفاً فایل را با مدل دیگری "
                    f"دوباره آپلود کنید، یا متن درخواست را به‌صورت تایپی ارسال کنید.\n"
                )
                continue

            # 🔴 (extraction-100pct-fix v2) — کاربر گزارش داد ۹۰٪+ محتوای
            # فایل‌های آپلودی به task نمی‌رسید با cap 1MB. اول 50MB کردیم
            # ولی این از context window همهٔ مدل‌ها بزرگ‌تر بود (Gemini 2.5
            # Pro = 2M token ≈ 6MB UTF-8، Claude = 200K ≈ 600KB، GPT-4o =
            # 128K ≈ 400KB). 50MB یعنی request یا fail می‌شد یا silently
            # truncate می‌شد.
            #
            # **استراتژی v2**:
            # - cap 5MB: ~5x بزرگ‌تر از 1MB قبلی، در محدودهٔ Gemini 2.5 Pro
            #   جا می‌شه (با حاشیه برای system prompt + سایر context)
            # - برای documentهای بزرگتر از 5MB، متن کامل در DB هست،
            #   می‌شه با چندین task جداگانه پردازش کرد
            # - هشدار صریح اگر متن > 500KB
            FILE_CAP = 5_000_000  # 5MB — متناسب با context window مدل‌ها
            head = full_text[:FILE_CAP]
            tail_note = ""
            if len(full_text) > FILE_CAP:
                # فقط فایل‌های واقعاً غول‌پیکر (>50MB) tail note می‌گیرن
                tail_note = (
                    f"\n\n_[…متن کامل ({len(full_text):,} char) در DB است. "
                    f"این بخش اول {FILE_CAP//1_000_000}MB از متن است؛ بقیه با "
                    f"extraction_id={fe.id} از /extractions/{{id}}/full-text قابل دسترسی است.]_"
                )
            # 🆕 (extraction-100pct-fix) — اگر متن بزرگه (>500KB)، یک یادآور
            # صریح به مدل تولید پرامپت می‌چسبونیم تا همهٔ بخش‌ها رو در
            # task task_steps پوشش بده و خلاصه‌سازی مخرب انجام نده.
            _completeness_warning = ""
            if len(head) > LARGE_IDEA_CHARS:
                _completeness_warning = (
                    f"\n\n⚠️ **این فایل بزرگ است ({len(head):,} char). برای synthesis:**\n"
                    f"- **هیچ بخشی را drop نکن** — همهٔ topics/sections/items "
                    f"در task_steps منعکس بشن.\n"
                    f"- **خلاصه‌سازی مخرب ممنوع** — اگر فایل ۲۰۰ مورد داره، "
                    f"task_steps هم باید ۲۰۰ مورد رو پوشش بده (یا "
                    f"group بندی صریح کنه ولی هیچ موردی حذف نشه).\n"
                    f"- **تعداد steps محدود نیست** — نیاز شد، ۵۰ یا ۱۰۰ step بساز.\n"
                )
            appended_parts.append(
                f"\n\n## 📎 فایل پیوست #{s.file_order}: {s.original_filename}\n"
                f"_mime={s.mime_type} • model={fe.model_used} • "
                f"{fe.total_segments} segment استخراج شد • "
                f"{len(head):,} char متن_\n"
                f"{_completeness_warning}\n"
                f"{head}{tail_note}"
            )

        if appended_parts:
            augmented = (
                idea
                + "\n\n---\n## 📎 فایل‌های پیوست (به ترتیب آپلود = ترتیب بخش‌ها)"
                + "".join(appended_parts)
            )
        else:
            augmented = idea
        return augmented, attachments_meta

    # ====================================================================
    # 🔔 Reminder feature
    # ====================================================================

    async def _idea_to_prompt_reminder(
        self,
        *,
        idea: str,
        priority: str,
        model_id: Optional[str],
        upload_session_ids: Optional[List[str]],
        attachments_meta: List[Dict[str, Any]],
        progress_track_id: Optional[str],
    ) -> Dict[str, Any]:
        """مسیر اختصاصی برای type=="reminder".

        خروجی JSON با شکل:
          {
            "title": str,        # عنوان کوتاه یادآوری
            "summary": str,      # شرح کوتاه (1-3 جمله)
            "checklist": List[str],  # action items قابل تیک
          }
        سپس با build_strong_prompt(type_="reminder", ...) به متن
        پرامپت (که در واقع متن یادآوری است) تبدیل می‌شود.
        """
        from .ai_manager import get_ai_manager
        from .ai_base import Message
        from .oversight_strong_prompt import build_strong_prompt

        # title پیش‌فرض از اولین خط idea
        first_line = (idea or "").strip().splitlines()[:1]
        default_title = (first_line[0] if first_line else "یادآوری")[:80]

        # انتخاب مدل: اگر فایل پیوست بود، حتماً مدل بصری
        effective_model = model_id
        if attachments_meta:
            try:
                from ..core.models_registry import (
                    pick_best_extraction_model, DEFAULT_EXTRACTION_MODEL_ID,
                )
                from .oversight_settings import (
                    get_default_extraction_model_id_from_db,
                )
                user_default = get_default_extraction_model_id_from_db()
                first_mime = (
                    attachments_meta[0].get("mime_type") or "image/png"
                ).lower()
                pref = user_default or DEFAULT_EXTRACTION_MODEL_ID
                m = pick_best_extraction_model(first_mime, preferred_model_id=pref)
                if m is not None:
                    effective_model = m.id
            except Exception as e:
                logger.debug(f"reminder: vision model pick failed: {e}")

        if not effective_model:
            from ..core.models_registry import get_default_model_id
            effective_model = get_default_model_id()

        # System prompt یادآوری‌محور
        # 🆕 (Reminder via Telegram) — علاوه بر title/summary/checklist،
        # AI باید زمان یادآوری (reminder_at به ISO UTC) و قاعدهٔ تکرار
        # (reminder_repeat_rule از {daily, weekly, null}) را از متن کاربر
        # استخراج کند. این برای ساخت تسک Telegram-driven ضروری است چون
        # کاربر در /reminder فقط متن می‌فرستد، نه datetime-picker جدا.
        from datetime import datetime as _dt_now, timezone as _tz_now
        _now_iso_for_prompt = _dt_now.now(_tz_now.utc).isoformat(timespec="seconds")
        system_content = (
            "تو یک دستیار شخصی هستی. کاربر یک یادآوری توصیف می‌کند "
            "(احتمالاً شامل پیام صوتی یا فایل پیوست). وظیفهٔ تو این است "
            "که آن را به یک ساختار ساده و قابل تیک تبدیل کنی — مثل "
            "to-do list شخصی. این یادآوری برای انجام کارهای روزمره "
            "است، نه برای engineer کدنویس.\n\n"
            f"اکنون (UTC): {_now_iso_for_prompt} — برای محاسبهٔ زمان‌های "
            "نسبی مثل «فردا»، «آخر هفته»، «۲ ساعت دیگر» استفاده کن.\n\n"
            "خروجی JSON معتبر با ساختار زیر بده (هیچ متن دیگری بیرون JSON ننویس):\n"
            "{\n"
            '  "title": "<عنوان کوتاه ≤80 کاراکتر؛ خلاصهٔ مفهوم یادآوری>",\n'
            '  "summary": "<شرح کوتاه 1-3 جمله که چرا/برای چه این یادآوری است>",\n'
            '  "checklist": ["<آیتم اول>", "<آیتم دوم>", ...],\n'
            '  "reminder_at": "<ISO 8601 UTC مثل 2026-05-20T14:30:00+00:00 — '
            'زمان firing بعدی؛ null اگر کاربر زمان نگفت>",\n'
            '  "reminder_repeat_rule": "<\\"daily\\" | \\"weekly\\" | null>"\n'
            "}\n\n"
            "قواعد سخت‌گیرانه:\n"
            "1. هر آیتم چک‌لیست باید یک action واحد، کوتاه (≤120 کاراکتر)، "
            "و قابل تیک باشد — مثل «به فلانی زنگ بزن» یا «دارو بخر».\n"
            "2. هیچ‌چیز را خلاصه نکن — اگر کاربر ۸ مورد گفت، ۸ آیتم بده.\n"
            "3. ترتیب آیتم‌ها = ترتیبی که کاربر گفت (مگر یک ترتیب طبیعی‌تر باشد).\n"
            "4. نام‌ها، URLها، آدرس‌ها، اعداد را verbatim حفظ کن.\n"
            "5. این یک تسک کدنویسی نیست — هیچ ارجاع به فایل/تابع/repo نده.\n"
            "6. اگر متن کاربر فقط یک کار است، فقط یک آیتم در checklist بگذار.\n"
            "7. **زمان‌بندی**: اگر کاربر گفت «هر روز ساعت ۹»، repeat=daily و "
            "reminder_at را روی نزدیک‌ترین ۹ صبح آینده ست کن. اگر گفت «هر "
            "هفته جمعه»، repeat=weekly و reminder_at را روی نزدیک‌ترین جمعه. "
            "اگر گفت «فردا» بدون ساعت، ساعت ۹ صبح فردا. اگر هیچ زمانی "
            "نگفت، reminder_at=null بگذار (سیستم پیش‌فرض می‌گذارد)."
        )

        # 🔔 اگر فایل پیوست داشت، augment idea با محتوای استخراج‌شده
        # (resolve_attachments قبلاً انجام شده — متن در idea تزریق شده است)
        user_content = (
            "متن کاربر (همراه استخراج فایل پیوست در صورت موجود بودن):\n\n"
            f"{idea}\n\n"
            "JSON معتبر برگردان."
        )

        messages = [
            Message(role="system", content=system_content),
            Message(role="user", content=user_content),
        ]

        mgr = get_ai_manager()
        try:
            resp = await mgr.generate(
                model_id=effective_model,
                messages=messages,
                max_tokens=4000,
                temperature=0.2,
                allow_fallback=False,
            )
            raw = (resp.content or "").strip()
        except Exception as e:
            logger.warning(f"reminder AI failed: {e}")
            raw = ""

        title = default_title
        summary = idea[:300]
        checklist: List[str] = []
        reminder_at_extracted: Optional[str] = None
        reminder_repeat_extracted: Optional[str] = None
        try:
            import re as _re_rem
            m = _re_rem.search(r"\{.*\}", raw, _re_rem.DOTALL)
            if m:
                data = json.loads(m.group(0))
                title = (data.get("title") or default_title)[:80]
                summary = (data.get("summary") or summary)[:1000]
                cl = data.get("checklist") or []
                if isinstance(cl, list):
                    # 🆕 (bug 30 v3) — cap reminder checklist هم به ۱۰۰ بالا برد
                    checklist = [str(x)[:200] for x in cl if str(x).strip()][:100]
                # 🆕 (Reminder via Telegram) — datetime extraction
                _r_at = data.get("reminder_at")
                if isinstance(_r_at, str) and _r_at.strip() and _r_at.lower() != "null":
                    # تأیید parseable بودن — اگر خراب بود، None می‌گذاریم.
                    # همچنین اگر زمان استخراج‌شده در گذشته بود (AI گاهی
                    # ساعت را بدون توجه به امروز/فردا می‌گذارد)، یک قاعدهٔ
                    # نرم اعمال می‌کنیم: اگر <1 دقیقه گذشته → null تا
                    # caller default 1 ساعت بعد بگذارد؛ اگر کمتر از ۲۴
                    # ساعت گذشته → +1 روز forward (احتمالاً منظور AI همان
                    # ساعت روز بعد بوده).
                    try:
                        from datetime import datetime as _dt_v, timedelta as _td_v, timezone as _tz_v
                        _parsed = _dt_v.fromisoformat(_r_at.replace("Z", "+00:00"))
                        if _parsed.tzinfo is None:
                            _parsed = _parsed.replace(tzinfo=_tz_v.utc)
                        _now_v = _dt_v.now(_tz_v.utc)
                        _delta = (_parsed - _now_v).total_seconds()
                        if _delta < -60 and _delta > -86400:
                            # کمتر از یک روز گذشته — احتمالاً منظور AI همان
                            # ساعت روز بعد بوده. forward by 1 day.
                            _parsed = _parsed + _td_v(days=1)
                            reminder_at_extracted = _parsed.isoformat()
                            logger.info(
                                f"reminder_at adjusted +1 day: {_r_at} → {reminder_at_extracted}"
                            )
                        elif _delta < -86400:
                            # خیلی در گذشته — null کن تا default بخورد
                            logger.debug(
                                f"reminder_at far in past: {_r_at} — ignored"
                            )
                        else:
                            reminder_at_extracted = _parsed.isoformat()
                    except Exception as _de:
                        logger.debug(f"reminder_at extraction unparseable: {_r_at} ({_de})")
                _r_rule = data.get("reminder_repeat_rule")
                if isinstance(_r_rule, str) and _r_rule.lower() in ("daily", "weekly"):
                    reminder_repeat_extracted = _r_rule.lower()
        except Exception as e:
            logger.warning(f"reminder JSON parse failed: {e}")

        # اگر AI شکست خورد، fallback مینیمال: idea به‌عنوان title، یک
        # آیتم چک‌لیست از idea
        if not checklist:
            if idea and idea.strip():
                checklist = [idea.strip()[:200]]
            else:
                checklist = ["انجام کار یادآوری‌شده"]

        # ساخت task_steps با ساختار همخوان با verifier (هر استپ id/status)
        task_steps: List[Dict[str, Any]] = []
        for i, item in enumerate(checklist, start=1):
            task_steps.append({
                "id": i,
                "title": item,
                "scope": item,
                "status": "pending",
                "completion_pct": 0,
                "remaining": item,
                "done": False,  # 🔔 reminder-specific tick flag
            })

        # ساخت پرامپت یادآوری با build_strong_prompt(type_="reminder", ...)
        prompt_text = build_strong_prompt(
            title=title,
            raw_user_request=idea,
            description=summary,
            acceptance_criteria=checklist,
            type_="reminder",
            priority=priority,
        )

        return {
            "title": title,
            "prompt": prompt_text,
            "type": "reminder",
            "priority": priority,
            "raw_idea": idea,
            "target_files": [],
            "acceptance_criteria": checklist,
            "task_steps": task_steps,
            "overall_completion_pct": 0,
            "models_used": [effective_model] if effective_model else [],
            "attachments_meta": attachments_meta,
            # 🆕 (Reminder via Telegram) — زمان و تکرار استخراج‌شده از متن
            # کاربر (ممکن است None باشد اگر کاربر زمان نگفت — caller
            # تصمیم می‌گیرد پیش‌فرض بگذارد یا از کاربر بپرسد).
            "reminder_at": reminder_at_extracted,
            "reminder_repeat_rule": reminder_repeat_extracted,
        }

    async def idea_to_prompt(
        self,
        idea: str,
        watched_id: Optional[str],
        type_: str = "other",
        priority: str = "medium",
        model_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
        multi_pass_mode: str = "auto",  # 🆕 "auto" | "always" | "never"
        _skip_multi_pass: bool = False,  # internal flag — جلوگیری از recursion
        # 🆕 (Stage 7 — File Attachment Integration) — وقتی فایل پیوست شده،
        # extraction قبلاً انجام شده (یا اینجا انجام می‌شود) و متن کامل
        # هر فایل به‌ترتیب file_order به idea append می‌شود.
        upload_session_ids: Optional[List[str]] = None,
        # 🆕 (Stage 6) — اگر داده شد، progress updates روی این track_id ثبت می‌شود
        progress_track_id: Optional[str] = None,
        # 🆕 (perf fix) — skip deep_context (60-file GitHub fetch ~20-40s).
        # برای regenerate سریع super-task که content از قبل ساختاریافته است.
        _skip_deep_context: bool = False,
        # 🆕 (Reference Projects) — پروژه‌های انتخاب‌شده به‌عنوان منبع الهام.
        # هر آیتم: {project_id, project_path, is_selected}. اگر داده شود،
        # محتوای پروژه‌های مرجع scan + classify می‌شود و fusion text به idea
        # اضافه می‌شود تا AI بتواند ساختار و الگوها را الهام بگیرد.
        selected_projects: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not idea.strip() and not upload_session_ids:
            raise ValueError("ایده خالی است")
        if not idea.strip():
            idea = "[ایدهٔ متنی خالی — تحلیل فایل‌های پیوست]"

        # 🆕 پیش از multi-pass، فایل‌های پیوست را resolve کن
        attachments_meta: List[Dict[str, Any]] = []
        idea_was_empty_initially = not idea.strip() or idea.strip().startswith(
            "[ایدهٔ متنی خالی"
        )
        if upload_session_ids:
            try:
                idea, attachments_meta = await self._resolve_attachments_for_idea(
                    idea, upload_session_ids,
                    progress_track_id=progress_track_id,
                )
            except ValueError as _att_e:
                # 🛡 (audit fix CRITICAL) — اگر blocked_no_vision_model است،
                # exception را propagate کن تا API route 409 برگرداند.
                if getattr(_att_e, "blocked_payload", None) is not None:
                    raise
                logger.warning(f"idea_to_prompt: attachment resolve failed: {_att_e}")
            except Exception as _att_e:
                logger.warning(f"idea_to_prompt: attachment resolve failed: {_att_e}")

        # 🛡 (audit fix CRITICAL) — اگر کاربر متن نفرستاد و **همهٔ** فایل‌های
        # پیوست در استخراج fail شدند، اجازه نده prompt-builder بر اساس
        # پیام‌های خطا یک پرامپت توهمی بسازد. به‌جای آن یک خطای واضح
        # برگردان تا UI/Telegram به کاربر بگوید یا با مدل دیگر دوباره
        # تلاش کند یا متن را تایپی بفرستد.
        if (
            attachments_meta
            and idea_was_empty_initially
            and all(
                (m.get("all_segments_failed") or m.get("error"))
                for m in attachments_meta
            )
        ):
            failed_names = [
                m.get("filename") or f"file#{m.get('file_order')}"
                for m in attachments_meta
            ]
            err = ValueError(
                "استخراج **هیچ‌یک** از فایل‌های پیوست موفق نبود و متن کاربر "
                "هم خالی است — تولید پرامپت متوقف شد تا از پرامپت توهمی "
                "(بر اساس پیام‌های خطا) جلوگیری شود.\n"
                f"فایل‌ها: {', '.join(failed_names)}\n"
                "راه‌حل: یک مدل بصری دیگر (مثلاً gemini-2.5-pro) از /models "
                "انتخاب کنید و دوباره ارسال کنید، یا متن درخواست را به‌صورت "
                "تایپی همراه فایل ارسال کنید."
            )
            setattr(err, "blocked_payload", {
                "reason": "all_extractions_failed",
                "failed_files": failed_names,
                "attachments_meta": attachments_meta,
            })
            raise err

        # 🛡 (audit fix #3 CRITICAL) — اگر فایل پیوست هست، **همیشه** multi-pass
        # اجبار می‌شود تا چک‌لیست تولید شود. heuristic `_is_complex_idea` کافی
        # نیست چون متن کاربر می‌تواند کوتاه باشد ولی محتوای فایل‌ها طولانی.
        if attachments_meta and multi_pass_mode == "auto":
            multi_pass_mode = "always"
            logger.info(
                f"idea_to_prompt: attachments present ({len(attachments_meta)} files) "
                f"→ force multi_pass_mode='always' برای تضمین checklist"
            )

        # 🔔 (Reminder feature) — اگر type_=="reminder"، مسیر اختصاصی:
        # AI با system prompt یادآوری‌محور (نه code-grounded) اجرا می‌شود.
        # خروجی: title + description + checklist (action items)، بدون
        # target_locations/AC تکنیکی/risks/validation_commands. حلقهٔ
        # multi-pass code-grounded برای reminder بی‌معناست.
        if (type_ or "").lower().strip() == "reminder":
            return await self._idea_to_prompt_reminder(
                idea=idea,
                priority=priority,
                model_id=model_id,
                upload_session_ids=upload_session_ids,
                attachments_meta=attachments_meta,
                progress_track_id=progress_track_id,
            )

        # 🆕 (Reference Projects) — اگر کاربر پروژه‌های مرجع انتخاب کرده،
        # scan + classify + fusion را اجرا کن و خلاصهٔ ساختاریافته را به
        # idea اضافه کن. AI سپس می‌تواند الگوها/فایل‌ها/معماری پروژه‌های
        # مرجع را به‌عنوان منبع الهام ببیند و در پرامپت نهایی reflect کند.
        # تمام failures silently تحمل می‌شوند تا یک GitHub timeout روند
        # تولید پرامپت را قطع نکند.
        _normalized_refs = self._normalize_selected_projects(
            selected_projects, exclude_watched_id=watched_id,
        ) if selected_projects else []
        if _normalized_refs:
            try:
                from .reference_project_service import get_reference_project_service
                _ref_svc = get_reference_project_service()
                # 🆕 (current_project_profile) — شناسنامهٔ پروژهٔ فعلی برای
                # تطبیق توصیه‌ها با stack/dependency واقعی این پروژه.
                _cur_profile = self._build_current_project_profile(watched_id)
                _ref_ctx = await _ref_svc.build_reference_context(
                    selected_projects=_normalized_refs,
                    task_summary=idea[:500],
                    token=get_github_token() or None,
                    current_project_profile=_cur_profile,
                )
                if _ref_ctx and _ref_ctx.fusion_text:
                    idea = (
                        f"{idea}\n\n"
                        f"---\n"
                        f"## 📚 پروژه‌های مرجع (الهام از پیاده‌سازی‌های موجود)\n"
                        f"_در زیر خلاصهٔ ساختار/فایل‌های پروژه‌های زیر آمده است. "
                        f"از این منابع به‌عنوان الگو/الهام استفاده کن و در پرامپت نهایی "
                        f"به فایل‌ها/الگوهای مرتبط ارجاع بده._\n\n"
                        f"{_ref_ctx.fusion_text}\n"
                        f"---\n"
                    )
                    logger.info(
                        f"idea_to_prompt: injected reference context for "
                        f"{len(_normalized_refs)} project(s), {_ref_ctx.total_chars} chars"
                    )
            except Exception as _ref_e:
                logger.warning(f"idea_to_prompt: reference projects scan failed: {_ref_e}")

        # 🆕 (Stage 10 audit fix #1 — CRITICAL) — وقتی فایل پیوست هست، طبق
        # درخواست صریح کاربر، **همهٔ کارها از تبدیل به پرامپت تا شرح فایل**
        # باید با مدل بصری (Gemini یا جایگزین پویا) انجام شود — نه با مدل
        # عمومی که کاربر در UI انتخاب کرده. اگر model_id کاربر مدل بصری
        # نیست، آن را با بهترین مدل extraction جایگزین می‌کنیم.
        if attachments_meta:
            try:
                from ..core.models_registry import (
                    pick_best_extraction_model, mime_to_required_capability,
                    DEFAULT_EXTRACTION_MODEL_ID, get_model, MODEL_REGISTRY,
                )
                from .oversight_settings import get_default_extraction_model_id_from_db
                # اولویت: تنظیمات کاربر در DB > preferred default > heuristic
                user_default = get_default_extraction_model_id_from_db()
                target_pref = user_default or DEFAULT_EXTRACTION_MODEL_ID
                # mime عمومی برای picker: اگر ترکیبی است، MULTIMODAL را بخواه
                first_mime = (attachments_meta[0].get("mime_type") or "image/png").lower()
                m = pick_best_extraction_model(
                    first_mime, preferred_model_id=target_pref
                )
                if m is not None:
                    # وقتی فایل پیوست هست، حتماً از مدل بصری استفاده می‌کنیم
                    if model_id != m.id:
                        logger.info(
                            f"idea_to_prompt: فایل پیوست → جایگزینی model_id "
                            f"از '{model_id}' به مدل بصری '{m.id}' (طبق درخواست کاربر)"
                        )
                    model_id = m.id
                    # model_ids هم اگر داده شده، fallbackها باید همگی vision باشند
                    # یا حذف شوند تا multi-pass به اشتباه مدل ضعیف استفاده نکند
                    if model_ids:
                        from ..core.models_registry import (
                            list_extraction_model_candidates,
                        )
                        vision_ids = [
                            c.id for c in list_extraction_model_candidates(
                                first_mime, include_disabled=False
                            )
                        ]
                        model_ids = [mi for mi in model_ids if mi in vision_ids]
                        if not model_ids:
                            model_ids = [m.id]
            except Exception as _force_e:
                logger.warning(f"force-vision-model logic failed: {_force_e}")

        # 🆕 (Multi-pass) — تقسیم به مراحل کوچک برای کیفیت بهتر.
        # سه حالت با parameter `multi_pass_mode`:
        #   "auto" (default): اگر heuristic (طول، bullet، URL، connectors) پیچیدگی
        #     تشخیص داد، multi-pass. وگرنه single-pass (سریع‌تر).
        #   "always": همیشه multi-pass — حتی idea ساده. AI پلن می‌سازد، اگر فقط
        #     ۱ step تشخیص داد، خودکار به single-pass fallback می‌شود.
        #   "never": همیشه single-pass — overhead AI plan ندارد.
        #
        # `_skip_multi_pass` parameter (نه instance attribute) برای concurrency-safety.
        # 🛡 (audit fix CRITICAL) — کاربر صریحاً خواسته که چک‌لیست **همیشه**
        # روی اولین ارسال هم ساخته شود (همان رفتار تلگرام). heuristic قبلی
        # `_is_complex_idea` برای ایده‌های کوتاه (مثل «این باگ را رفع کن»)
        # multi-pass را trigger نمی‌کرد و کاربر برای هر ایدهٔ کوتاه مجبور به
        # «بازتولید» می‌شد. حالا mode="auto" را معادل "always" می‌گیریم.
        # اگر کاربر صریحاً "never" پاس کند، single-pass باقی می‌ماند.
        mode = (multi_pass_mode or "auto").lower().strip()
        if mode == "auto":
            mode = "always"
        should_try_multi_pass = (
            not _skip_multi_pass
            and mode == "always"
        )
        if should_try_multi_pass:
            try:
                result = await self._idea_to_prompt_multi_pass(
                    idea=idea,
                    watched_id=watched_id,
                    type_=type_,
                    priority=priority,
                    model_id=model_id,
                    model_ids=model_ids,
                )
                if result:
                    if attachments_meta:
                        result["attachments"] = attachments_meta
                        result["upload_session_ids"] = upload_session_ids or []
                    return result
            except Exception as _mp_e:
                logger.warning(
                    f"idea_to_prompt: multi-pass fail ({_mp_e}) — fallback به single-pass"
                )

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
            #
            # 🆕 (perf fix) — برای regenerate سریع super-task این مرحله
            # skip می‌شود (20-40s صرفه‌جویی + جلوگیری از Render edge timeout).
            # content super-task از قبل ساختاریافته است و نیازی به re-fetch
            # 60 فایل از GitHub ندارد.
            if _skip_deep_context:
                logger.info(
                    f"idea_to_prompt: deep_context skipped (fast-path requested) "
                    f"watched={watched.id}"
                )
            else:
                try:
                    token_for_deep = get_github_token()
                    if token_for_deep:
                        from .oversight_deep_scan_service import build_deep_context_for_idea
                        # 🛡 (audit fix #1) — context عمیق‌تر و گسترده‌تر:
                        # 40 → 60 فایل، per-file byte cap 50K → 120K، خط 350 → 800
                        deep_ctx = await build_deep_context_for_idea(
                            watched.repo_full_name,
                            branch=watched.default_branch or "main",
                            token=token_for_deep,
                            max_deep_read=60,        # افزایش از 40
                            max_file_bytes=120000,   # افزایش از 50K — هر فایل ~120KB
                            max_file_lines=800,      # افزایش از 350 — فایل‌های بزرگ بهتر دیده شوند
                            idea=idea,  # keyword-aware file selection
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

        # 🆕 (Reference Projects — system prompt) — اگر کاربر پروژه‌های مرجع
        # انتخاب کرده، fusion text در idea injection شده است. system prompt
        # باید AI را صریحاً ملزم کند که:
        #   1. بخش پروژه‌های مرجع را در description ذکر کند (نه drop)
        #   2. در proposed_action هشدار adapt-to-current-stack بنویسد
        #   3. در risks خطر mixing stack/dependency را ذکر کند
        #   4. هرگز syntax/dependency مرجع را blind copy نکند
        # تشخیص: header fusion service `## 📚 پروژه‌های مرجع` در idea.
        _reference_block = ""
        if "## 📚 پروژه‌های مرجع" in idea or "Reference Projects" in idea:
            _reference_block = (
                "\n\n# 🔵 قانون پروژه‌های مرجع (CRITICAL — کاربر صریحاً پروژه‌های دیگر را به‌عنوان الهام انتخاب کرده)\n"
                "متن user حاوی بخش `## 📚 پروژه‌های مرجع (Reference Projects)` است که "
                "خلاصهٔ ساختار/فایل/الگوهای **پروژه‌های دیگری** را در بر دارد. این پروژه‌ها "
                "**پروژهٔ مقصد نیستند** — فقط منبع الهام هستند. تو باید:\n\n"
                "**قوانین مطلق**:\n"
                "1. **بخش «پروژه‌های مرجع» را در description ذکر کن** — لیست نام پروژه‌ها، "
                "چرا کاربر انتخاب‌شان کرده، و کدام الگو/فایل/feature از آنها قرار است الهام شود. "
                "هرگز این بخش را silent drop نکن.\n"
                "2. **در proposed_action، صریحاً هشدار تطبیق با stack فعلی بنویس**. "
                "مثال: «الگوی X از پروژهٔ مرجع foo/bar الهام گرفته شده — قبل از پیاده‌سازی، باید "
                "به stack فعلی پروژه (مثلاً Next.js App Router به جای Pages Router مرجع، یا "
                "FastAPI به جای Flask) adapt شود. هرگز import یا syntax کورکورانه از مرجع کپی "
                "نشود.»\n"
                "3. **در risks، خطر mixing dependency/naming/stack را explicit ذکر کن**. "
                "مثال: «اگر developer الگوی auth از پروژهٔ مرجع X را بدون تطبیق با ORM فعلی پیاده "
                "کند، migration ناسازگار می‌شود.»\n"
                "4. **در tech_context، تفاوت‌های کلیدی stack مرجع vs فعلی را ذکر کن** "
                "(مثل: «مرجع Flask است، فعلی FastAPI — endpoint signature متفاوت است»).\n"
                "5. **در acceptance_criteria، یک معیار اضافه کن**: «الگوی برداشت‌شده از پروژهٔ مرجع "
                "با dependency و naming پروژهٔ فعلی سازگار است (نه copy-paste صرف).»\n"
                "6. **هرگز یک reference به پروژهٔ مرجع را به‌عنوان path پروژهٔ فعلی استفاده نکن**. "
                "فایل‌های ذکرشده در fusion text **برای الهام** هستن، نه برای ویرایش. "
                "target_locations فقط فایل‌های پروژهٔ فعلی است.\n\n"
                "**هدف**: کاربر می‌خواهد بداند الهام از کجا گرفته شده، و developer نباید بدون توجه "
                "به differences پیاده‌سازی کند. این یک سیگنال صریح است که الگو **شناخته‌شده ولی "
                "نیازمند adapt** است.\n"
            )

        # 🔴 (extraction-100pct-fix) — اگر فایل پیوست داره، یک قانون صریح
        # اضافه می‌کنیم به system prompt تا synthesis از روی متن کامل پیوست
        # ساخته بشه، نه خلاصه‌ای از idea.
        _attachment_block = ""
        if "📎 فایل پیوست" in idea:
            _attachment_block = (
                "\n\n# 🔴🔴 قانون پیوست (CRITICAL — کاربر گزارش داد ۹۰٪+ محتوای فایل گم می‌شه)\n"
                "متن user حاوی بخش‌های `## 📎 فایل پیوست #N` است که محتوای **استخراج‌شده "
                "از فایل‌های آپلودی** هستن. این محتوا **بخش اصلی درخواست** کاربر است.\n\n"
                "**قوانین مطلق**:\n"
                "1. **هیچ بخش/مورد/topic از پیوست drop نکن**. اگه فایل ۲۰۰ آیتم داره، "
                "task_steps باید ۲۰۰ مورد رو پوشش بده (یا با grouping صریح، ولی هیچی "
                "حذف نشه).\n"
                "2. **task_steps تعدادش محدود نیست** — برای فایل بزرگ، 30-100 step "
                "هم منطقی است. کم گفتن = شکست.\n"
                "3. **description باید همهٔ section های پیوست رو reference بده** "
                "(نام‌بردن از hint های `## بخش X` یا `## فایل پیوست #N`).\n"
                "4. **acceptance_criteria باید verifiable برای هر بخش پیوست باشه** — "
                "نه فقط top-level «task انجام شد».\n"
                "5. **هرگز خلاصه‌سازی مخرب نکن** مثل «و موارد مشابه از فایل پیوست» — "
                "هر مورد رو explicit بنویس.\n"
                "6. اگر پیوست بزرگه و JSON خروجی محدودیت ظرفیت داره، task_steps رو "
                "به sub-tasks تقسیم کن (با `parent_step_id`) — نه drop.\n"
            )

        system_prompt = f"""تو یک معمار ارشد نرم‌افزاری هستی که به repository واقعی پروژه دسترسی داری. وظیفه‌ات این است که ایده/مشکل/درخواست خام کاربر را به یک تسک ساختاریافتهٔ **مبتنی بر کد واقعی پروژه** تبدیل کنی — نه یک پرامپت عمومی.

خروجی این تسک به یک ابزار کدنویس خارجی (Cursor/Copilot/ChatGPT) داده می‌شود — پس فیلدها باید **کاملاً مشخص، grounded در کد واقعی، و قابل اعمال** باشند.
{_attachment_block}
{_reference_block}
# 🧠 چارچوب فکر کردن (الزامی — قبل از تولید JSON، این مراحل را ذهنی طی کن)

**مرحله ۱ — تحلیل کامل متن کاربر** (هیچ‌چیز را skip نکن):
- *چه می‌خواهد؟* — کاربر دقیقاً چه کاری می‌خواهد انجام شود؟ یک مورد یا چند مورد؟
- *کجا؟* — کدام صفحه، endpoint، فایل، component، service خاص اشاره شده؟
- *کلیدواژه‌ها چیست؟* — همهٔ URL ها، آدرس‌ها، نام‌ها (فایل، تابع، endpoint، repo، service، library)، error message ها
- *Context چیست؟* — «وقتی Y رخ می‌دهد»، «در حالت Z»، «بعد از W»، شرایط واقعی استفاده
- *نشانه‌های مشکل؟* — error log، behavior غلط، expectation متفاوت
- *چه دلیلی؟* — کاربر چرا این را می‌خواهد؟ پشت ظاهر مسئله، علت اصلی چیست؟

**مرحله ۲ — مطابقت با کد واقعی** (deep_context را عمیق بخوان):
- کدام فایل‌ها از deep_context با درخواست کاربر مرتبط است؟
- ساختار آن فایل‌ها چیست؟ کدام function/class/import روی این تأثیر می‌گذارد؟
- کدام فایل‌ها این موارد را call می‌کنند یا state share می‌کنند؟
- چه stack و libraries استفاده شده؟ آیا approach کاربر با این stack سازگار است؟
- نقاط risk کدام‌ها هستند؟ تغییر این کد روی چه چیزی اثر می‌گذارد؟

**مرحله ۳ — طراحی راه‌حل**:
- دقیق‌ترین تغییرات چه هستند؟ کدام خط‌ها، توابع، فایل‌ها؟
- چه ترتیبی برای پیاده‌سازی منطقی است؟
- چه تست‌هایی باید برای verify اضافه/تنظیم شوند؟
- معیارهای پذیرش قابل اندازه‌گیری چه چیست؟

**مرحله ۴ — ساخت خروجی**:
- وقتی JSON می‌سازی، هر فیلد را با outputهای ۳ مرحلهٔ بالا پر کن
- **پاسخ سطحی غیرقابل قبول است** — اگر description تو ۳ جمله است، می‌فهمم که عمیق فکر نکرده‌ای
- **اگر deep_context داده شده، باید حداقل ۵ فایل واقعی reference کنی** (در target_locations + related_files)

# 🚨 قانون طلایی (نقض = شکست تسک)
**متن خام کاربر مرجع اصلی است.** تو فقط ساختار اضافه می‌کنی، **هرگز اطلاعات را نمی‌حذفی**:

1. **همهٔ URL ها، لینک‌ها، آدرس‌ها** که کاربر ذکر کرده، در `description` کپی شوند — verbatim، بدون تغییر.
2. **همهٔ نام‌ها** (نام فایل، تابع، endpoint، repo، sandbox، service خاص) که کاربر گفته، در `description` تکرار شوند.
3. **همهٔ context** که کاربر داده، در `description` حفظ شود.
4. **هرگز** کلمات اختصاصی را با مترادف عمومی جایگزین نکن.
5. `description` باید **حداقل ۸۰٪** حجم متن خام کاربر را داشته باشد + توضیحات تو.
6. اگر کاربر چندین مورد گفته (مثلاً ۵ تغییر)، **همهٔ ۵ مورد** ذکر شوند.

ساختار تو، **پوشش** متن کاربر است، نه **جایگزینی** آن.

# 📏 معیارهای کیفیت قابل اندازه‌گیری (پاسخ‌های زیر این آستانه‌ها رد می‌شوند)

| فیلد | حداقل |
|---|---|
| `description` | ≥ 500 کاراکتر، شامل: تحلیل + کلیدواژه‌های کاربر + شواهد در کد |
| `proposed_action` | ≥ 300 کاراکتر، با مراحل عددی واضح |
| `target_locations` | ≥ 2 مورد با path واقعی + snippet کد واقعی + lines |
| `related_files` | ≥ 3 مورد با reason مشخص |
| `acceptance_criteria` | ≥ 4 مورد قابل تست، نه عمومی |
| `dependency_summary` | ≥ 200 کاراکتر، با نام واقعی فایل‌ها |
| `risks` | ≥ 100 کاراکتر، با ذکر فایل/تابع — نه «احتیاط در deploy» |

اگر deep_context موجود است و این آستانه‌ها را رعایت نکنی، **پاسخ سطحی است**.

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

# 📋 Context کلی پروژه
{ctx_text or 'پروژه مشخص نیست'}
{deep_block}

# 💬 ایده/درخواست خام کاربر (مرجع اصلی — هیچ‌چیز را حذف نکن)
نوع: {type_}
اولویت: {priority}
متن:
\"\"\"
{idea.strip()}
\"\"\"

# 📤 خروجی فقط JSON خالص (بدون متن اضافی، بدون ```)

{{
  "title": "عنوان کوتاه و گویا تسک — حداکثر ۸ کلمه با ساختار 'فعل عملیاتی + موضوع مشخص + scope روشن'. مثال خوب: 'افزودن دکمهٔ undo به super-task'. مثال بد: 'بهبود سیستم'، 'تغییرات'، 'fix'، 'update'، 'improve'. کلمات generic بدون context ممنوع — باید نوع‌بندی واضح موضوع باشد.",
  "description": "پاراگراف کامل + همهٔ URL ها/آدرس‌ها/نام‌ها از متن کاربر + شواهد در کد واقعی پروژه (نام فایل و خط ذکر کن). حداقل ۸۰٪ متن کاربر در اینجا باید بازتاب پیدا کند.",
  "proposed_action": "پیشنهاد عملی برای پیاده‌سازی — با ذکر فایل‌ها/توابع واقعی + همهٔ URL/آدرس از متن کاربر",
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
    {{
      "text": "معیار قابل تست ۱ — با مرجع به فایل/تابع واقعی",
      "verify_method": "static | ui_interaction | api_response | backend_test | manual_only",
      "verify_plan": {{ /* وابسته به verify_method — به راهنمای پایین مراجعه کن */ }}
    }},
    "معیار ۲ به‌صورت رشته‌ای ساده — اگر method خاصی نمی‌دانی، فقط رشته بنویس و پیش‌فرض static گرفته می‌شود"
  ],

  "validation_commands": ["pytest backend/...", "npm run test -- ..."],

  "risks": "ریسک‌های specific این کدبیس (نه جملات عمومی) — مثلاً 'این تابع توسط ۳ روتر استفاده می‌شود، تغییرش روی همه اثر دارد'"
}}
{deep_rules_block}

# 🔬 راهنمای انتخاب verify_method (Stage 2 — Runtime Verify Layer)
**هر AC ماهیتی دارد. AC را به یکی از ۵ متد ببر:**

| نشانه‌ها در متن AC | verify_method | verify_plan باید شامل باشد |
|---|---|---|
| «فایل X وجود دارد»، «import شده»، «class Y تعریف شده» | `static` | `{{"grep_patterns": ["pattern1", "pattern2"], "files_hint": ["path/to/file.py"]}}` |
| «کلیک»، «نمایش»، «مودال باز شود»، «صفحه X لود شود» | `ui_interaction` | `{{"ui_steps": [{{"action": "navigate", "url": "/path"}}, {{"action": "click", "selector": "[data-testid='x']"}}, {{"action": "wait_for", "selector": "[role='dialog']"}}, {{"action": "assert_visible", "selector": "..."}}]}}` |
| «endpoint Y returns 200»، «API X با شِما Z پاسخ می‌دهد» | `api_response` | `{{"method": "GET", "path": "/api/...", "expected_status": 200, "required_fields": ["id", "name"]}}` |
| «تست T pass شود»، «pytest tests/X.py» | `backend_test` | `{{"test_path": "backend/tests/test_x.py::test_func", "marker": "verify"}}` |
| AC مبهم/ذهنی («ظاهر زیبا»، «UX خوب»، «قابل فهم باشد») | `manual_only` | `{{"reason": "subjective — needs human review"}}` |

**نمونه‌های few-shot:**

AC = «دکمهٔ Login باید modal باز کند»:
```json
{{
  "text": "دکمهٔ Login باید modal باز کند",
  "verify_method": "ui_interaction",
  "verify_plan": {{
    "ui_steps": [
      {{"action": "navigate", "url": "/"}},
      {{"action": "click", "selector": "[data-testid='btn-login']"}},
      {{"action": "wait_for", "selector": "[role='dialog']", "timeout_ms": 3000}},
      {{"action": "assert_visible", "selector": "[role='dialog']"}}
    ]
  }}
}}
```

AC = «GET /api/users → 200 با field email»:
```json
{{
  "text": "GET /api/users → 200 با field email",
  "verify_method": "api_response",
  "verify_plan": {{
    "method": "GET",
    "path": "/api/users",
    "expected_status": 200,
    "required_fields": ["email"]
  }}
}}
```

AC = «class OversightTask باید فیلد verify_method داشته باشد»:
```json
{{
  "text": "class OversightTask باید فیلد verify_method داشته باشد",
  "verify_method": "static",
  "verify_plan": {{
    "grep_patterns": ["verify_method:", "verify_method =", "class OversightTask"],
    "files_hint": ["backend/app/services/oversight_service.py"]
  }}
}}
```

AC = «طراحی شیک‌تر باشد»:
```json
{{
  "text": "طراحی شیک‌تر باشد",
  "verify_method": "manual_only",
  "verify_plan": {{"reason": "subjective — needs human review"}}
}}
```

**اگر مطمئن نیستی، `static` با `grep_patterns` بساز** (fallback ایمن — همیشه قابل اجراست).
نکته: حداقل ۵۰٪ از AC ها باید verify_method **غیر** از manual_only داشته باشند (تا verify خودکار بتواند کار کند).

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
            # 🆕 max_tokens بالاتر برای پرامپت‌های غنی (description >=500، target_locations
            # با snippet کد واقعی، AC چندتایی، …)
            # 🔴 (extraction-100pct-fix) — اگر فایل پیوست بزرگ داریم (>500KB idea)،
            # output budget رو به 64K می‌بریم. کاربر گفت «هزینه مهم نیست». این
            # برای task با 100+ step از فایل‌های بزرگ ضروری است.
            _has_large_attachment = len(idea) > LARGE_IDEA_CHARS
            if _has_large_attachment:
                grounded_max_tokens = 64000  # برای task های با ۵۰+ step
            elif deep_ctx.get("ok"):
                grounded_max_tokens = 16000
            else:
                grounded_max_tokens = 10000
            # 🆕 temperature خیلی پایین برای grounding بیشتر در deep_context واقعی
            grounded_temperature = 0.1 if deep_ctx.get("ok") else 0.25
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

            # 🆕 detection truncation: stringها را در نظر می‌گیرد
            # (شمارش ساده count("{") نادرست است چون snippet ها می‌توانند {} داشته باشند)
            def _looks_truncated(resp: str) -> bool:
                if not resp or len(resp) < 100:
                    return False
                stripped = resp.rstrip().rstrip(" `\n")
                if not stripped.endswith(("}", "]")):
                    return True
                # پیمایش با احترام به stringها
                depth = 0
                in_str = False
                esc = False
                for c in stripped:
                    if in_str:
                        if esc:
                            esc = False
                        elif c == "\\":
                            esc = True
                        elif c == '"':
                            in_str = False
                    else:
                        if c == '"':
                            in_str = True
                        elif c in "{[":
                            depth += 1
                        elif c in "}]":
                            depth -= 1
                if in_str:
                    return True
                if depth != 0:
                    return True
                # سعی parse — اگر بازم خطا می‌دهد، احتمالاً truncated است
                try:
                    json.loads(stripped)
                    return False
                except Exception:
                    # ممکن است JSON valid باشد ولی با extra prefix/suffix
                    start = stripped.find("{")
                    end = stripped.rfind("}")
                    if start != -1 and end > start:
                        try:
                            json.loads(stripped[start:end + 1])
                            return False
                        except Exception:
                            return True
                    return True

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

        from .oversight_strong_prompt import build_strong_prompt, EXECUTOR_DISCLAIMER

        parsed = self._extract_json(response)

        # 🆕 (Quality Check) ارزیابی عمق پاسخ بر اساس معیارهای کیفیت قابل اندازه‌گیری
        # علاوه بر چک ناقص بودن، عمق هر فیلد را اندازه می‌گیریم — اگر سطحی، retry با feedback specific
        def _evaluate_quality(p: Dict[str, Any], raw_idea: str) -> Tuple[bool, List[str]]:
            """خروجی: (is_quality_acceptable, feedback_issues_list)
            مشکلات گزارش‌شده در feedback به AI نشان داده می‌شود تا retry بهبود دهد.
            """
            issues: List[str] = []
            if not isinstance(p, dict):
                return False, ["JSON معتبر نیست"]

            desc = (p.get("description") or "").strip()
            if len(desc) < 500:
                issues.append(
                    f"`description` فقط {len(desc)} کاراکتر است (حداقل ۵۰۰ نیاز است). "
                    f"باید شامل: تحلیل کامل + همهٔ URL/نام‌های کاربر + شواهد در کد"
                )

            pa = (p.get("proposed_action") or "").strip()
            if len(pa) < 300:
                issues.append(
                    f"`proposed_action` فقط {len(pa)} کاراکتر است (حداقل ۳۰۰). "
                    f"باید مراحل عددی واضح داشته باشد"
                )

            tl = p.get("target_locations") or []
            if not isinstance(tl, list) or len(tl) < 2:
                issues.append(
                    f"`target_locations` فقط {len(tl) if isinstance(tl, list) else 0} مورد. حداقل ۲ مورد"
                )
            else:
                missing_snippet = sum(
                    1 for x in tl if isinstance(x, dict) and not (x.get("snippet") or "").strip()
                )
                if missing_snippet > len(tl) // 2:
                    issues.append(
                        f"{missing_snippet} از {len(tl)} target_locations بدون snippet هستند. "
                        f"از deep_context کد واقعی کپی کن"
                    )

            rf = p.get("related_files") or []
            if not isinstance(rf, list) or len(rf) < 3:
                issues.append(
                    f"`related_files` فقط {len(rf) if isinstance(rf, list) else 0} مورد. حداقل ۳ مورد با reason"
                )

            ac = p.get("acceptance_criteria") or []
            if not isinstance(ac, list) or len(ac) < 4:
                issues.append(
                    f"`acceptance_criteria` فقط {len(ac) if isinstance(ac, list) else 0} مورد. حداقل ۴ مورد قابل تست"
                )

            dep = (p.get("dependency_summary") or "").strip()
            if len(dep) < 200:
                issues.append(
                    f"`dependency_summary` فقط {len(dep)} کاراکتر. حداقل ۲۰۰ با نام فایل‌ها"
                )

            # حفظ کلیدواژه‌های کاربر در description
            raw_lower = (raw_idea or "").lower()
            desc_lower = desc.lower()
            # استخراج URL ها از raw_idea
            import re as _re
            urls_in_raw = _re.findall(r'https?://[^\s\)\]\}]+', raw_idea or "")
            missing_urls = [u for u in urls_in_raw if u.lower() not in desc_lower]
            if missing_urls:
                issues.append(
                    f"URL های کاربر در description نیامده‌اند: {', '.join(missing_urls[:3])}"
                )

            return (len(issues) == 0), issues

        # چک ناقص بودن primary
        critical_keys = {"description", "target_locations", "acceptance_criteria"}
        parsed_keys = set(parsed.keys()) if isinstance(parsed, dict) else set()
        is_too_thin = (
            not parsed
            or not parsed_keys
            or len(parsed_keys & critical_keys) < 2
            or not (parsed.get("description") or "").strip()
        )

        # quality check جدید — حتی اگر JSON کامل بود، عمق پاسخ را اندازه می‌گیریم
        quality_ok, quality_issues = (False, []) if is_too_thin else _evaluate_quality(parsed, idea)
        needs_retry = is_too_thin or not quality_ok

        # 🆕 (perf fix) — برای fast-path (super-task یا idea بزرگ)، strict-retry
        # را skip می‌کنیم تا total time در محدودهٔ Render edge timeout (30s)
        # بماند. strict-retry یک AI call دوم می‌زند که 5-15s اضافی می‌گیرد.
        # برای super-task content از قبل ساختاریافته است و quality bar پایین‌تر
        # قابل قبول است.
        if needs_retry and _skip_deep_context:
            logger.info(
                "idea_to_prompt: strict-retry skipped (fast-path requested) "
                f"despite thin={is_too_thin}, quality_issues={len(quality_issues)}"
            )
            needs_retry = False

        if needs_retry:
            logger.warning(
                f"idea_to_prompt: نیاز به retry — "
                f"thin={is_too_thin}, quality_issues={len(quality_issues)}"
            )
            try:
                issues_text = ""
                if quality_issues:
                    issues_text = "\n".join(f"   ❌ {i}" for i in quality_issues[:8])
                strict_suffix = (
                    f"\n\n# 🚨 توجه: پاسخ قبلی سطحی/ناقص بود.\n"
                    f"این بار با دقت بیشتر و عمق کافی تولید کن.\n\n"
                    f"## مشکلات پاسخ قبلی:\n{issues_text}\n\n"
                    f"## این بار:\n"
                    f"1. فقط یک JSON object معتبر — هیچ متن قبل/بعد JSON نباشد.\n"
                    f"2. هیچ ``` یا توضیح اضافه نباشد.\n"
                    f"3. `description` باید >= 500 کاراکتر باشد — تحلیل عمیق + همهٔ URL/نام‌های کاربر\n"
                    f"4. `target_locations` حداقل ۲ مورد با snippet کد واقعی از deep_context\n"
                    f"5. `related_files` حداقل ۳ مورد با reason دقیق\n"
                    f"6. `acceptance_criteria` حداقل ۴ مورد قابل تست\n"
                    f"7. `dependency_summary` >= 200 کاراکتر با نام فایل‌های واقعی\n"
                    f"8. **همهٔ URL/لینک از متن کاربر در description باشند** (verbatim)\n"
                    f"9. JSON با }} بسته شود — هیچ field ناقص نگذار.\n"
                )
                retry_max2 = min(20000, grounded_max_tokens + 6000)
                if effective_models and len(effective_models) > 1:
                    multi2 = await self._ai_generate_multi(
                        system_prompt + strict_suffix,
                        model_ids=effective_models,
                        max_tokens=retry_max2,
                        temperature=grounded_temperature,
                    )
                    best2 = max(
                        (m for m in multi2 if not m.get("error") and m.get("content")),
                        key=lambda m: len(m["content"]),
                        default=None,
                    )
                    response2 = best2["content"] if best2 else ""
                else:
                    response2 = await self._ai_generate(
                        system_prompt + strict_suffix,
                        model_id=(effective_models[0] if effective_models else None),
                        max_tokens=retry_max2,
                        temperature=grounded_temperature,
                    )
                if response2 and len(response2) > 200:
                    parsed2 = self._extract_json(response2)
                    if isinstance(parsed2, dict):
                        # 🆕 quality comparison: parsed2 را با parsed قبلی مقایسه کن
                        # هر کدام عمیق‌تر، نگه دار. اگر هر دو سطحی، parsed2 (تازه) را نگه دار.
                        if not isinstance(parsed, dict) or not parsed:
                            parsed = parsed2
                            response = response2
                            logger.info("idea_to_prompt: retry replaced empty/invalid parsed")
                        else:
                            # امتیاز عمق: طول description + تعداد target_locations + تعداد AC
                            def _depth_score(p: Dict[str, Any]) -> int:
                                desc_len = len((p.get("description") or "").strip())
                                tl = p.get("target_locations") or []
                                rf = p.get("related_files") or []
                                ac = p.get("acceptance_criteria") or []
                                return (
                                    desc_len
                                    + (len(tl) if isinstance(tl, list) else 0) * 200
                                    + (len(rf) if isinstance(rf, list) else 0) * 100
                                    + (len(ac) if isinstance(ac, list) else 0) * 80
                                )
                            score_old = _depth_score(parsed)
                            score_new = _depth_score(parsed2)
                            if score_new > score_old:
                                parsed = parsed2
                                response = response2
                                logger.info(
                                    f"idea_to_prompt: retry بهتر بود "
                                    f"(score {score_old} → {score_new})"
                                )
                            else:
                                logger.info(
                                    f"idea_to_prompt: retry بهبود نداشت "
                                    f"(score {score_new} <= {score_old}) — نسخهٔ اول حفظ شد"
                                )
            except Exception as _strict_e:
                logger.warning(f"idea_to_prompt strict retry failed: {_strict_e}")

        if not parsed or not isinstance(parsed, dict):
            # 🆕 fallback ایمن: به جای دامپ raw response آلوده،
            # یک پرامپت ساختاریافتهٔ صریح بساز که کاربر بداند AI درست عمل نکرده
            # و بتواند regenerate بزند.
            logger.error("idea_to_prompt: AI نتوانست JSON معتبر تولید کند")
            safe_title = (idea.strip().split("\n")[0])[:80] or "تسک بدون عنوان"
            safe_prompt_body = (
                f"## هدف\n{idea.strip()}\n\n"
                "## ⚠️ توجه: AI خروجی JSON معتبر تولید نکرد\n"
                "این پرامپت minimal است. لطفاً:\n"
                "- روی دکمهٔ «🔄 بازتولید» کلیک کنید (با مدل دیگر یا raw_idea بیشتر)\n"
                "- یا پرامپت را دستی ویرایش کنید\n\n"
                "## معیار پذیرش\n- (تعریف نشده — لطفاً regenerate یا edit کنید)\n"
            )
            result_minimal = {
                "title": safe_title,
                "prompt": EXECUTOR_DISCLAIMER + "\n" + safe_prompt_body,
                "target_files": [],
                "target_locations": [],
                "related_files": [],
                "acceptance_criteria": [],
                "type": type_,
                "priority": priority,
                "estimate": "medium",
                "raw_response": response,
                "_quality_flag": "json_parse_failed",
                # 🆕 idea نهایی پس از resolve_attachments — شامل متن کاربر +
                # متن استخراج‌شدهٔ همهٔ فایل‌های پیوست (صوت/PDF/...). callerها
                # باید این را به‌جای ورودی خام به raw_idea تسک بدهند تا
                # transcript فایل صوتی یا extract فایل از دست نرود.
                "raw_idea": idea,
            }
            if attachments_meta:
                result_minimal["attachments"] = attachments_meta
                result_minimal["upload_session_ids"] = upload_session_ids or []
            return result_minimal

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
            raw_user_request=idea,  # 🆕 متن خام کاربر — verbatim حفظ می‌شود
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

        result_final = {
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
            # 🆕 تعداد واقعی فایل‌های deep-read شده تا UI به‌جای متن hardcoded
            # «۱۸ فایل»، تعداد واقعی را نشان دهد
            "deep_files_count": len(deep_ctx.get("deep_paths", [])) if isinstance(deep_ctx, dict) else 0,
            # 🆕 idea نهایی پس از resolve_attachments — شامل متن کاربر +
            # متن استخراج‌شدهٔ همهٔ فایل‌های پیوست. callerها (Telegram bot
            # و frontend) باید این را به‌جای ورودی خام به raw_idea تسک بدهند
            # تا transcript صوت/extract PDF/OCR تصویر در ایدهٔ ثبت‌شده باقی
            # بماند و برای بازتولید قابل دسترسی باشد.
            "raw_idea": idea,
        }
        if attachments_meta:
            result_final["attachments"] = attachments_meta
            result_final["upload_session_ids"] = upload_session_ids or []
        return result_final

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
    # 🔗 Bug C7 — Bridge: Inspector ↔ Oversight helpers
    # ====================================================================

    async def build_followup_for_task(
        self,
        task: "OversightTask",
        last_report: Optional["OversightReport"] = None,
    ) -> str:
        """ساخت پرامپت followup مختصر برای ادامهٔ کار روی یک تسک.

        خروجی: متن چند خطی که در smart-chat در round بعدی ping-pong یا
        execute فرستاده می‌شود. شامل:
          - تأیید آنچه done شد (done_parts)
          - تمرکز روی آنچه remaining است (remaining_parts)
          - فایل‌هایی که قبلاً تغییر کرد (تا overwrite نشود)
        """
        # اگر last_report داده نشده، آخرین report تسک را پیدا کن
        if last_report is None:
            last_report = next(
                (r for r in self.reports if r.task_id == task.id), None
            )

        lines: List[str] = []
        lines.append("# ادامهٔ کار روی تسک")
        lines.append(f"عنوان: {task.title}")
        lines.append("")

        # آنچه done شد
        done_parts: List[str] = []
        if last_report and getattr(last_report, "done_parts", None):
            done_parts = list(last_report.done_parts)
        if done_parts:
            lines.append("## ✓ بخش‌هایی که در round های قبل انجام شدند")
            lines.append("این موارد را **دوباره** پیاده‌سازی نکنید — فقط بدانید کامل‌اند:")
            for dp in done_parts[:20]:
                dp_text = str(dp).strip()
                if dp_text:
                    lines.append(f"  - {dp_text[:200]}")
            lines.append("")

        # آنچه باقی مانده — مهم‌ترین بخش
        remaining_parts: List[str] = []
        if last_report and getattr(last_report, "remaining_parts", None):
            remaining_parts = list(last_report.remaining_parts)
        if remaining_parts:
            lines.append("## ⚠️ بخش‌هایی که باید الان انجام شوند (تمرکز کامل اینجا)")
            for i, rp in enumerate(remaining_parts, 1):
                rp_text = str(rp).strip()
                if rp_text:
                    lines.append(f"  {i}. {rp_text}")
            lines.append("")
        else:
            # remaining خالی است ولی verify done نشده — یعنی AC ها هست ولی
            # هیچ AC در remaining ست نشده. کل AC را به‌عنوان hint بده.
            ac_list = list(task.acceptance_criteria or [])
            if ac_list:
                lines.append("## 📋 acceptance_criteria کامل (هنوز done کامل نشده)")
                for i, ac in enumerate(ac_list, 1):
                    if isinstance(ac, dict):
                        ac_text = ac.get("text", "") or str(ac)
                    else:
                        ac_text = str(ac)
                    if ac_text.strip():
                        lines.append(f"  {i}. {ac_text.strip()[:300]}")
                lines.append("")

        # فایل‌های قبلاً تغییر داده‌شده — تا overwrite نشود
        evidence = task.applied_evidence or {}
        prev_files: List[str] = list(evidence.get("files_committed") or [])
        if prev_files:
            lines.append("## 🛡 فایل‌هایی که در apply قبلی تغییر کردند")
            lines.append("این فایل‌ها قبلاً modify شدند. اگر باز هم لازم است "
                         "تغییر دهید، **افزایشی** کار کنید — کد موجود را پاک نکنید:")
            for fp in prev_files[:30]:
                lines.append(f"  - {fp}")
            lines.append("")

        # یک reminder صریح در پایان
        lines.append("---")
        lines.append(
            "**لطفاً دقیقاً همان فرمت action تولید کنید "
            "(action_plan با files = [{path, content, operation}])** "
            "تا apply-action بتواند آن را به‌کار ببرد."
        )

        return "\n".join(lines)

    async def execute_task_via_inspector(
        self,
        task_id: str,
        *,
        model_ids: Optional[List[str]] = None,
        followup_only: bool = False,
    ) -> Dict[str, Any]:
        """اجرای یک تسک از طریق پایپ‌لاین smart-chat inspector.

        این تابع برای ping-pong loop scheduler است (فاز ۴ Bridge). به‌جای
        فراخوانی run_task مستقیم (که فقط verdict تولید می‌کند)، تسک را به
        smart-chat می‌فرستد تا کد تولید + apply شود.

        Args:
          task_id: شناسهٔ تسک
          model_ids: اگر None، از watched.default_model_ids استفاده می‌شود
          followup_only: اگر True، فقط followup ارسال می‌شود (round بعدی)

        Returns:
          dict با status و جزئیات اجرا
        """
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task is None:
            return {"success": False, "error": "task not found"}

        watched = self._find_watched(task.watched_id) if task.watched_id else None
        if not watched:
            return {"success": False, "error": "watched project not found for task"}

        # ساخت پیام به smart-chat
        if followup_only:
            last_report = next(
                (r for r in self.reports if r.task_id == task_id), None
            )
            message = await self.build_followup_for_task(task, last_report)
        else:
            message = (
                f"# اجرای تسک از مرکز نظارت\n\n"
                f"این تسک از مرکز نظارت برای اجرا فرستاده شده. "
                f"لطفاً action تولید کنید تا apply-action کد را اعمال کند.\n\n"
                f"## تسک:\n{task.title}\n\n"
                f"## prompt:\n{task.prompt[:5000]}"
            )

        # یافتن project_id از watched.repo_full_name
        # نکته: oversight tasks در DB با watched_id لینک اند، نه با project_id.
        # inspector با project_id کار می‌کند. اگر watched.repo_full_name با
        # project.github_path یا extra_data.owner/repo match شود، آن project
        # را پیدا می‌کنیم. در نسخه‌های بعد می‌توان wired-link کرد.
        # برای الان، resolver ساده:
        try:
            from ..core.database import SessionLocal
            from ..models.project import Project as _Proj_lookup
            _db = SessionLocal()
            try:
                _projects = _db.query(_Proj_lookup).all()
                project_id: Optional[str] = None
                target_path = (watched.repo_full_name or "").lower()
                for p in _projects:
                    if (p.github_path or "").lower() == target_path:
                        project_id = p.id
                        break
                    # هم extra_data را چک کن
                    try:
                        ed = p.extra_data
                        if isinstance(ed, str):
                            ed = json.loads(ed)
                        if isinstance(ed, dict):
                            _o = (ed.get("owner") or "").lower()
                            _r = (ed.get("repo") or "").lower()
                            if _o and _r and f"{_o}/{_r}" == target_path:
                                project_id = p.id
                                break
                    except Exception:
                        continue
            finally:
                _db.close()
        except Exception as _pe:
            logger.warning(f"execute_task_via_inspector: project lookup failed: {_pe}")
            project_id = None

        if not project_id:
            return {
                "success": False,
                "error": f"no inspector project found for watched.repo_full_name={watched.repo_full_name}",
            }

        # NOTE: smart-chat یک SSE streaming endpoint است. در ping-pong scheduler
        # ما نمی‌توانیم مستقیماً SSE consumer باشیم بدون HTTP client overhead.
        # راه‌حل: smart-chat را با کاهش-فرم به یک تابع داخلی refactor کنیم،
        # یا یک HTTP client از خود سرور به خودش بزنیم. برای minimum viable
        # implementation، یک HTTP self-call می‌زنیم.
        import os as _os
        backend_base = _os.environ.get("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000")
        try:
            import aiohttp as _ah
            _payload = {
                "project_id": project_id,
                "model_ids": list(model_ids or []),
                "message": message,
                "task_id": task_id,
            }
            _timeout = _ah.ClientTimeout(total=600)
            async with _ah.ClientSession(timeout=_timeout) as session:
                async with session.post(
                    f"{backend_base}/api/render/inspector/smart-chat",
                    json=_payload,
                ) as r:
                    if r.status != 200:
                        return {
                            "success": False,
                            "error": f"smart-chat HTTP {r.status}",
                        }
                    # SSE consumer — تا done event بخوان
                    accumulated: List[str] = []
                    async for chunk in r.content.iter_chunked(8192):
                        try:
                            accumulated.append(chunk.decode("utf-8", errors="ignore"))
                        except Exception:
                            pass
                        if "event: done" in "".join(accumulated[-3:]):
                            break
            return {
                "success": True,
                "task_id": task_id,
                "project_id": project_id,
                "message_chars": len(message),
                "raw_response_length": sum(len(c) for c in accumulated),
            }
        except Exception as _he:
            return {
                "success": False,
                "error": f"smart-chat call failed: {_he}",
            }

    # ====================================================================
    # 🆕 (C7v2 Sections 4+5) — Auto-sync memory/training + review cycle
    # ====================================================================

    def _resolve_inspector_project_id(
        self, watched_id: str
    ) -> Optional[str]:
        """🆕 (C7v2) یافتن inspector project مرتبط با یک watched.

        match روی github_path یا extra_data.{owner,repo} انجام می‌شود.
        خروجی: project_id یا None.
        """
        watched = self._find_watched(watched_id)
        if not watched or not watched.repo_full_name:
            return None
        target = (watched.repo_full_name or "").lower()
        try:
            from ..core.database import SessionLocal
            from ..models.project import Project as _Proj_rs
            _db = SessionLocal()
            try:
                for p in _db.query(_Proj_rs).all():
                    if (p.github_path or "").lower() == target:
                        return p.id
                    try:
                        ed = p.extra_data
                        if isinstance(ed, str):
                            ed = json.loads(ed)
                        if isinstance(ed, dict):
                            _o = (ed.get("owner") or "").lower()
                            _r = (ed.get("repo") or "").lower()
                            if _o and _r and f"{_o}/{_r}" == target:
                                return p.id
                    except Exception:
                        continue
            finally:
                _db.close()
        except Exception as _re:
            logger.warning(f"_resolve_inspector_project_id failed: {_re}")
        return None

    async def sync_to_inspector_memory_training(
        self, watched_id: str
    ) -> Dict[str, Any]:
        """🆕 (C7v2 Section 4) سینک خودکار memory و training از مرکز نظارت.

        منابع:
          - memory ← watched.user_notes + OversightCodex (تنها زمانی که
            متن در ≥۲ scan/report ظاهر شده)
          - training ← key_changes از تسک‌های done (تنها زمانی که در ≥۳
            تسک done تکرار شده)

        Trigger: انتهای scan_project و verify_task. هرگز timer مستقل.
        خروجی: {created_memory_count, created_training_count, skipped_count}.
        """
        project_id = self._resolve_inspector_project_id(watched_id)
        if not project_id:
            return {
                "created_memory_count": 0,
                "created_training_count": 0,
                "skipped_count": 0,
                "reason": "no inspector project for this watched",
            }

        watched = self._find_watched(watched_id)
        if not watched:
            return {
                "created_memory_count": 0,
                "created_training_count": 0,
                "skipped_count": 0,
                "reason": "watched not found",
            }

        try:
            from ..core.database import SessionLocal
            from ..models.inspector_prompt_field import InspectorPromptField
            from sqlalchemy import or_, func as _sql_func
        except Exception as _ie:
            logger.warning(f"sync_to_inspector: import failed: {_ie}")
            return {
                "created_memory_count": 0,
                "created_training_count": 0,
                "skipped_count": 0,
                "reason": f"import failed: {_ie}",
            }

        # ── memory candidates ──
        memory_candidates: List[Dict[str, Any]] = []
        # 1) user_notes (اگر هست و طولش معنادار است)
        notes = (getattr(watched, "user_notes", "") or "").strip()
        if notes and len(notes) >= 30:
            memory_candidates.append({
                "title": f"یادداشت کاربر: {watched.repo_full_name}",
                "content": notes[:2000],
                "evidence_source": "user_notes",
            })
        # 2) از OversightCodex (اگر سرویس‌اش موجود است)
        try:
            from .oversight_codex_service import (
                load_codex_for_project as _load_codex,
            )
            codex_data = _load_codex(watched.id)
            if isinstance(codex_data, dict):
                arch = (codex_data.get("architecture") or "").strip()
                if arch and len(arch) >= 30:
                    memory_candidates.append({
                        "title": f"معماری پروژه: {watched.repo_full_name}",
                        "content": arch[:2000],
                        "evidence_source": "codex",
                    })
        except Exception as _ce:
            logger.debug(f"sync: codex load skipped: {_ce}")

        # 🆕 (C7v3/Addendum v5 §1.6) — منابع جدید memory از Project metadata
        # (description, technologies, memory_instructions). این به پروژه‌های
        # جوان کمک می‌کند که حداقل ۱-۲ فیلد memory داشته باشند بدون نیاز به
        # ساخت دستی codex یا تکمیل user_notes.
        try:
            from ..core.database import SessionLocal as _SL_proj
            from ..models.project import Project as _Proj_meta
            _pdb = _SL_proj()
            try:
                _proj = _pdb.query(_Proj_meta).filter(_Proj_meta.id == project_id).first()
                if _proj:
                    _desc = (getattr(_proj, "description", "") or "").strip()
                    if _desc and len(_desc) >= 20:
                        memory_candidates.append({
                            "title": "شرح پروژه",
                            "content": _desc[:2000],
                            "evidence_source": "project_description",
                        })
                    _tech = (getattr(_proj, "technologies", "") or "").strip()
                    if _tech and len(_tech) >= 20:
                        memory_candidates.append({
                            "title": "تکنولوژی‌های پروژه",
                            "content": _tech[:2000],
                            "evidence_source": "project_technologies",
                        })
                    _mem_inst = (getattr(_proj, "memory_instructions", "") or "").strip()
                    if _mem_inst and len(_mem_inst) >= 20:
                        memory_candidates.append({
                            "title": "دستورات حافظهٔ پروژه",
                            "content": _mem_inst[:2000],
                            "evidence_source": "project_memory_instructions",
                        })
            finally:
                _pdb.close()
        except Exception as _pme:
            logger.debug(f"sync: project metadata load skipped: {_pme}")

        # ── training candidates ──
        # از key_changes تسک‌های done شده — شمارش تکرار
        done_tasks = [
            t for t in self.tasks
            if t.watched_id == watched_id
            and (t.verification_status or "") == "done"
        ]
        kc_counter: Dict[str, int] = {}
        for t in done_tasks:
            for r in self.reports:
                if r.task_id != t.id:
                    continue
                tc = getattr(r, "touched_codex", None) or {}
                if isinstance(tc, dict):
                    kcs = tc.get("key_changes") or []
                    if isinstance(kcs, list):
                        for kc in kcs[:10]:
                            kc_text = str(kc).strip()
                            if len(kc_text) >= 20:
                                kc_counter[kc_text] = kc_counter.get(kc_text, 0) + 1
        training_candidates: List[Dict[str, Any]] = []
        for kc_text, count in kc_counter.items():
            # 🆕 (C7v3/Addendum v5 §1.5) — آستانهٔ تکرار از ۳ به ۲ کاهش یافت
            # تا پروژه‌های جوان زودتر training داشته باشند.
            if count >= 2:
                training_candidates.append({
                    "title": kc_text[:80],
                    "content": kc_text,
                    "evidence_count": count,
                })

        # 🆕 (C7v3/Addendum v5 §1.7) — منبع training از action_plan_summary
        # تسک‌های done. هر summary پایدار (≥۵۰ کاراکتر) به‌عنوان training
        # candidate با evidence_count=1 اضافه می‌شود. به‌مرور تقویت می‌شود.
        for t in done_tasks:
            evidence = getattr(t, "applied_evidence", None) or {}
            if isinstance(evidence, dict):
                summary = (evidence.get("action_plan_summary") or "").strip()
                if summary and len(summary) >= 50:
                    # عنوان از اولین خط
                    first_line = summary.splitlines()[0][:80] if summary.splitlines() else summary[:80]
                    training_candidates.append({
                        "title": first_line,
                        "content": summary[:2000],
                        "evidence_count": 1,
                    })

        # ── ایجاد فیلدهای جدید (skip اگر موجود) ──
        created_mem = 0
        created_train = 0
        skipped = 0
        try:
            _db = SessionLocal()
            try:
                # memory
                for cand in memory_candidates:
                    # شرط تثبیت: متن باید در ≥۲ scan متوالی یا ≥۲ report ظاهر
                    # شده باشد. برای user_notes و codex، خود وجودش به
                    # معنای تثبیت توسط کاربر است (پایدار).
                    # check duplicate by title+content
                    existing = _db.query(InspectorPromptField).filter(
                        InspectorPromptField.project_id == project_id,
                        InspectorPromptField.category == "memory",
                        InspectorPromptField.title == cand["title"],
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                    new_f = InspectorPromptField(
                        project_id=project_id,
                        category="memory",
                        title=cand["title"],
                        content=cand["content"],
                        priority=5,
                        is_active=True,
                        archived=False,
                        source="oversight_auto_sync",
                        auto_synced=True,
                        evidence_count=2,
                        last_seen_at=datetime.utcnow(),
                    )
                    _db.add(new_f)
                    created_mem += 1
                # training
                for cand in training_candidates:
                    existing = _db.query(InspectorPromptField).filter(
                        InspectorPromptField.project_id == project_id,
                        InspectorPromptField.category == "training",
                        InspectorPromptField.title == cand["title"][:80],
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                    new_f = InspectorPromptField(
                        project_id=project_id,
                        category="training",
                        title=cand["title"][:80],
                        content=cand["content"],
                        priority=5,
                        is_active=True,
                        archived=False,
                        source="oversight_auto_sync",
                        auto_synced=True,
                        evidence_count=int(cand.get("evidence_count", 3)),
                        last_seen_at=datetime.utcnow(),
                    )
                    _db.add(new_f)
                    created_train += 1
                if created_mem > 0 or created_train > 0:
                    _db.commit()
            finally:
                _db.close()
        except Exception as _de:
            logger.warning(f"sync_to_inspector DB write failed: {_de}")

        logger.info(
            f"sync_to_inspector(watched={watched_id}): "
            f"created memory={created_mem}, training={created_train}, skipped={skipped}"
        )
        return {
            "created_memory_count": created_mem,
            "created_training_count": created_train,
            "skipped_count": skipped,
            "project_id": project_id,
        }

    async def review_auto_synced_fields(
        self, watched_id: str
    ) -> Dict[str, Any]:
        """🆕 (C7v2 Section 5) بازبینی فیلدهای auto-synced: بمانند/تقویت/آرشیو.

        منطق:
          - اگر content فیلد در reports/scans اخیر (۳۰ روز) دیده شد →
            تقویت: priority++, evidence_count++, last_seen_at=now
          - اگر last_seen_at > ۳۰ روز پیش بود → archive
          - اگر تناقض با key_changes جدید پیدا شد → archive

        Trigger: انتهای scan_project و verify_task. خروجی:
        {strengthened_count, archived_count, unchanged_count}.
        """
        project_id = self._resolve_inspector_project_id(watched_id)
        if not project_id:
            return {
                "strengthened_count": 0,
                "archived_count": 0,
                "unchanged_count": 0,
                "reason": "no inspector project",
            }

        try:
            from ..core.database import SessionLocal
            from ..models.inspector_prompt_field import InspectorPromptField
        except Exception as _ie:
            return {
                "strengthened_count": 0,
                "archived_count": 0,
                "unchanged_count": 0,
                "reason": f"import failed: {_ie}",
            }

        now = datetime.utcnow()
        threshold_30d = now - timedelta(days=30)

        # جمع‌آوری content های متون اخیر (reports/scans اخیر) برای match
        recent_corpus_parts: List[str] = []
        for r in self.reports[:50]:
            if r.task_id:
                task = next((t for t in self.tasks if t.id == r.task_id), None)
                if task and task.watched_id == watched_id:
                    if isinstance(r.evidence, dict):
                        for v in r.evidence.values():
                            if isinstance(v, str):
                                recent_corpus_parts.append(v)
                            elif isinstance(v, (list, dict)):
                                recent_corpus_parts.append(str(v))
        recent_corpus = "\n".join(recent_corpus_parts).lower()

        strengthened = 0
        archived = 0
        unchanged = 0

        try:
            _db = SessionLocal()
            try:
                auto_fields = _db.query(InspectorPromptField).filter(
                    InspectorPromptField.project_id == project_id,
                    InspectorPromptField.auto_synced == True,  # noqa: E712
                    InspectorPromptField.archived == False,  # noqa: E712
                ).all()
                for f in auto_fields:
                    # content match — اگر بخشی از title یا content در corpus
                    # اخیر دیده می‌شود → strengthen
                    title_lower = (f.title or "").lower()
                    content_lower = (f.content or "").lower()
                    seen = False
                    if title_lower and len(title_lower) >= 10 and title_lower in recent_corpus:
                        seen = True
                    elif content_lower:
                        # check first 100 chars of content
                        snippet = content_lower[:100]
                        if snippet and snippet in recent_corpus:
                            seen = True

                    if seen:
                        # تقویت
                        f.priority = min(int(f.priority or 0) + 1, 20)
                        f.evidence_count = int(f.evidence_count or 0) + 1
                        f.last_seen_at = now
                        strengthened += 1
                    elif f.last_seen_at and f.last_seen_at < threshold_30d:
                        # آرشیو (>۳۰ روز ندیده شد)
                        f.archived = True
                        archived += 1
                    elif not f.last_seen_at:
                        # last_seen_at خالی — اگر created_at بیش از ۳۰ روز
                        # پیش بود، archive کن
                        if f.created_at and f.created_at < threshold_30d:
                            f.archived = True
                            archived += 1
                        else:
                            unchanged += 1
                    else:
                        unchanged += 1
                if strengthened > 0 or archived > 0:
                    _db.commit()
            finally:
                _db.close()
        except Exception as _de:
            logger.warning(f"review_auto_synced_fields DB write failed: {_de}")

        logger.info(
            f"review_auto_synced_fields(watched={watched_id}): "
            f"strengthened={strengthened}, archived={archived}, unchanged={unchanged}"
        )
        return {
            "strengthened_count": strengthened,
            "archived_count": archived,
            "unchanged_count": unchanged,
            "project_id": project_id,
        }

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

    async def scan_project(
        self,
        watched_id: str,
        model_id: Optional[str] = None,
        *,
        selected_sections: Optional[List[str]] = None,
        custom_paths: Optional[List[str]] = None,
        include_dependencies: bool = True,
        focus_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """اسکن سریع پروژه.

        🆕 (selective-scan) اگر `selected_sections` یا `custom_paths` داده شوند،
        prompt مدل با محدودیت scope به همان بخش‌ها ساخته می‌شود تا تسک‌ها
        فقط روی همان zone متمرکز باشند. include_dependencies در quick scan
        فقط در عنوان scope ذکر می‌شود تا مدل آن را در تحلیل لحاظ کند
        (در deep scan با gراف import واقعی expand می‌شود).
        """
        watched = self._find_watched(watched_id)
        if not watched:
            raise ValueError("پروژه یافت نشد")

        # (audit fix #4) — وقتی scope داریم، نیاز به تره بزرگ‌تر داریم تا
        # سکشن‌های انتخابی واقعاً فایل match کنند. (پیش‌فرض ۸۰ بسیار کم بود
        # و انتخاب کاربر اغلب صفر فایل match می‌کرد، در حالی که endpoint
        # /sections از ۵۰۰ استفاده می‌کند → ناهمگنی.)
        _need_full_tree = bool(selected_sections or custom_paths)
        ctx = await self.build_project_context(
            watched.repo_full_name,
            max_tree=500 if _need_full_tree else 80,
        )

        # 🆕 (selective-scan) — اگر کاربر selection داده، files_sample را
        # محدود به همان بخش‌ها کن تا prompt هم محدود شود.
        scope_meta: Dict[str, Any] = {}
        if _need_full_tree:
            try:
                from .scan_sections import detect_sections, filter_files_by_selection
                all_files_for_scope = list(ctx.get("files_sample") or [])
                detected = detect_sections(all_files_for_scope)
                filtered = filter_files_by_selection(
                    all_files_for_scope,
                    selected_sections,
                    custom_paths,
                    detected_sections=detected,
                )
                if filtered:
                    ctx["files_sample"] = filtered[:80]
                    scope_meta = {
                        "selected_sections": list(selected_sections or []),
                        "custom_paths": list(custom_paths or []),
                        "include_dependencies": include_dependencies,
                        "scoped_files": len(filtered),
                        "total_files": len(all_files_for_scope),
                        "focus_notes": (focus_notes or "").strip() or None,
                    }
                else:
                    # (audit fix #4) — اگر selection هیچ فایلی match نکرد،
                    # silent fallback به اسکن کلی خطرناک است (prompt
                    # scope_block اضافه می‌کند ولی فایل‌ها همان full
                    # sample اند). خطای صریح بده تا کاربر متوجه شود.
                    raise ValueError(
                        "هیچ فایلی با selection match نشد. مسیر/section های انتخابی را بررسی کنید "
                        f"(checked {len(all_files_for_scope)} files in tree). "
                        f"sections={selected_sections}, custom_paths={custom_paths}"
                    )
            except ValueError:
                raise
            except Exception as _scope_err:
                # اگر فیلتر شکست خورد، scope را نادیده بگیر ولی scan را قطع نکن
                scope_meta = {"error": str(_scope_err)[:200]}

        # خلاصهٔ فایل‌های package برای تحلیل dependency
        package_summary = ""
        if ctx.get("package_files"):
            parts: List[str] = []
            for fname, content in (ctx["package_files"] or {}).items():
                parts.append(f"=== {fname} ===\n{content[:1500]}")
            package_summary = "\n\n".join(parts)

        # 🆕 (selective-scan) — اگر scope محدود است، یک بلوک به prompt اضافه کن
        scope_block = ""
        if scope_meta and (scope_meta.get("selected_sections") or scope_meta.get("custom_paths")):
            _ss = scope_meta.get("selected_sections") or []
            _cp = scope_meta.get("custom_paths") or []
            _inc = scope_meta.get("include_dependencies", True)
            _fn = scope_meta.get("focus_notes") or ""
            scope_block = (
                "\n# 🎯 محدودهٔ اسکن (Selective Scan)\n"
                "این یک اسکن **انتخابی** است — فقط روی این بخش‌ها/مسیرها تمرکز کن:\n"
                + (f"- بخش‌های انتخاب‌شده: {', '.join(_ss)}\n" if _ss else "")
                + (f"- مسیرهای سفارشی: {', '.join(_cp)}\n" if _cp else "")
                + (
                    "- 🔗 task های ساخته‌شده باید شامل **وابستگی‌ها** هم باشند: "
                    "هم فایل‌های انتخاب‌شده، هم فایل‌هایی که به آن‌ها متکی‌اند "
                    "(callers/importers)، هم فایل‌هایی که آن‌ها به آن متکی‌اند.\n"
                    if _inc
                    else "- task ها فقط روی فایل‌های انتخاب‌شده متمرکز باشند (بدون expand به وابستگی‌ها).\n"
                )
                + "- مشکلات یا تسک‌هایی که خارج از این scope هستند، حتی اگر مهم باشند، در این scan ذکر نکن.\n"
                + (
                    f"\n## ⚠️ توضیحات نقطه‌ای کاربر (از این بسیار جدی استفاده کن)\n"
                    f"کاربر دربارهٔ همین scope این یادداشت را داده — به این مشخصاً جواب بده، "
                    f"task ها را حول این موارد بساز، حتی اگر باگ هایی هم بیرون از این یادداشت دیدی، "
                    f"اولویت با این موارد است:\n\n{_fn.strip()}\n"
                    if _fn
                    else ""
                )
            )

        scan_prompt = f"""تو یک Senior Code Auditor و Security Engineer هستی. این پروژه را با دقت بررسی کن و یک فهرست کامل از «نیازها، ایرادات، تناقضات، آسیب‌پذیری‌ها و پیشنهادات بهبود» تهیه کن.

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{(watched.user_notes or '(کاربر یادداشتی ثبت نکرده است)').strip()}
{scope_block}
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

        # 🆕 (C7v2 Sections 4+5) — auto-sync + review در انتهای scan
        # این کار غیر-blocking است نسبت به نتیجهٔ scan؛ هر شکستی صرفاً log
        # می‌شود و scan موفق باقی می‌ماند.
        try:
            sync_result = await self.sync_to_inspector_memory_training(watched_id)
            logger.info(
                f"scan_project end → sync_to_inspector: "
                f"mem={sync_result.get('created_memory_count', 0)}, "
                f"train={sync_result.get('created_training_count', 0)}"
            )
        except Exception as _se:
            logger.warning(f"scan_project: sync_to_inspector failed: {_se}")
        try:
            review_result = await self.review_auto_synced_fields(watched_id)
            logger.info(
                f"scan_project end → review_auto_synced_fields: "
                f"strengthened={review_result.get('strengthened_count', 0)}, "
                f"archived={review_result.get('archived_count', 0)}"
            )
        except Exception as _re:
            logger.warning(f"scan_project: review_auto_synced_fields failed: {_re}")

        return {
            "success": True,
            "created_count": len(created_tasks),
            "tasks": created_tasks,
            "raw_response": response[:4000],
            # 🆕 (selective-scan) — اطلاعات scope برای نمایش در UI
            "scope": scope_meta or None,
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

        # 🆕 (Multi-pass Checklist) — اگر task_steps دارد، مراحل ناقص/انجام‌نشده
        # را به‌عنوان منبع اصلی remaining/AC استفاده کن. این focused تر است
        # چون مدل دقیقاً می‌داند چه مرحله‌ای را تکمیل کند.
        pending_steps: List[Dict[str, Any]] = []
        done_steps: List[Dict[str, Any]] = []
        for s in (task.task_steps or []):
            st = (s.get("status") or "pending").lower()
            if st == "done":
                done_steps.append(s)
            else:
                pending_steps.append(s)

        # اگر remaining خالی است، از next_actions به‌عنوان AC استفاده کن
        new_ac = list(remaining) if remaining else list(next_actions)
        if not new_ac:
            # fallback: AC های قبلی task که هنوز برآورده نشده‌اند
            new_ac = list(task.acceptance_criteria or [])
        if not new_ac:
            new_ac = ["تکمیل کامل خواسته‌های اصلی تسک"]
        # 🆕 اگر مراحل ناتمام داریم، AC را غنی‌تر کن
        if pending_steps:
            step_acs: List[str] = []
            for s in pending_steps:
                title = (s.get("title") or "").strip()
                rem = (s.get("remaining") or "").strip()
                if rem:
                    step_acs.append(f"[مرحله {s.get('id')} — {title}] باقی‌مانده: {rem[:200]}")
                else:
                    step_acs.append(f"[مرحله {s.get('id')} — {title}] {(s.get('scope') or '')[:200]}")
            # مراحل را پیش‌نشان (focus کاربر) و سپس remaining قبلی
            new_ac = step_acs + [a for a in new_ac if a not in step_acs]

        # description مفصل
        desc_parts: List[str] = []
        desc_parts.append(
            f"این پرامپت برای **دور {next_round}** ادامهٔ کار است. "
            "verifier در دور قبلی نشان داد کار به‌طور کامل انجام نشده."
        )
        # 🆕 (Multi-pass Checklist) — وضعیت چک‌لیست در صدر description
        if task.task_steps:
            overall = task.overall_completion_pct
            overall_str = f" — پیشرفت کلی: **{overall}%**" if overall is not None else ""
            check_lines = [
                f"📋 وضعیت چک‌لیست مراحل ({len(done_steps)}/{len(task.task_steps)} انجام‌شده){overall_str}:"
            ]
            for s in task.task_steps:
                st = (s.get("status") or "pending").lower()
                mark = "[x]" if st == "done" else ("[~]" if st == "partial" else "[ ]")
                line = f"  - {mark} **مرحله {s.get('id')}: {(s.get('title') or '')[:120]}**"
                if st != "done" and s.get("remaining"):
                    line += f" — باقی‌مانده: {(s.get('remaining') or '')[:200]}"
                check_lines.append(line)
            desc_parts.append("\n".join(check_lines))
            if pending_steps:
                desc_parts.append(
                    "🎯 **در این دور، فقط روی مراحل بالا که `[ ]` یا `[~]` دارند تمرکز کن.** "
                    "مراحلی که `[x]` خورده‌اند قبلاً تأیید شده‌اند — نگران آن‌ها نباش، "
                    "ولی regression نکن."
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
        # 🛡 (audit fix CRITICAL) — اگر build_strong_prompt fail کند، فالبک به
        # یک پرامپت مینیمال ولی قابل‌استفاده می‌دهیم، نه None. این تضمین می‌کند
        # task.prompt همیشه به یک نسخهٔ جدید به‌روز شود (با remaining steps).
        new_prompt: Optional[str] = None
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
            logger.warning(
                f"build_strong_prompt for follow-up failed: {_e} — استفاده از fallback مینیمال"
            )
            new_prompt = None
        # 🛡 fallback اگر build_strong_prompt هیچ‌چیز برنگرداند (None یا خالی)
        if not new_prompt or len(new_prompt.strip()) < 50:
            fb_parts: List[str] = []
            fb_parts.append(
                "## ⚠️ یادداشت\n"
                "این پرامپت یک نسخهٔ followup ساده‌شده است (build_strong_prompt fail شد)."
            )
            fb_parts.append("")
            fb_parts.append(f"# {new_title}")
            fb_parts.append("")
            fb_parts.append(new_description)
            fb_parts.append("")
            fb_parts.append("## ✅ معیارهای پذیرش باقی‌مانده (تمرکز این دور)")
            for a in new_ac[:20]:
                fb_parts.append(f"- [ ] {a}")
            if risks_text:
                fb_parts.append("")
                fb_parts.append("## ⚠️ ریسک‌ها / اقدامات پیشنهادی")
                fb_parts.append(risks_text)
            if validation_commands:
                fb_parts.append("")
                fb_parts.append("## 🧪 دستورات اعتبارسنجی")
                for c in validation_commands:
                    fb_parts.append(f"- `{c}`")
            new_prompt = "\n".join(fb_parts)

        # 🆕 (Multi-pass Checklist) — اگر task_steps هست، چک‌لیست را به انتهای
        # پرامپت append کن تا در دور بعدی verify بتواند checkbox‌ها را همگام کند.
        # وضعیت همان وضعیت فعلی است ([x] برای done، [~] برای partial، [ ] برای بقیه).
        if task.task_steps:
            checklist_lines: List[str] = [
                "",
                f"## 📋 چک‌لیست مراحل (دور {next_round})",
                "",
                "این مراحل از پرامپت اصلی نگه داشته شده‌اند تا verifier در هر دور "
                "وضعیت هر مرحله را به‌روز کند. `[x]` = انجام‌شده، `[~]` = ناقص، "
                "`[ ]` = هنوز انجام نشده.",
                "",
            ]
            for s in task.task_steps:
                st = (s.get("status") or "pending").lower()
                mark = "x" if st == "done" else ("~" if st == "partial" else " ")
                line = (
                    f"- [{mark}] **مرحله {s.get('id')}: "
                    f"{(s.get('title') or '')[:120]}** — "
                    f"{(s.get('scope') or '')[:300]}"
                )
                if st != "done" and s.get("remaining"):
                    line += f"\n      _باقی‌مانده: {(s.get('remaining') or '')[:200]}_"
                checklist_lines.append(line)
            new_prompt = (new_prompt or "") + "\n" + "\n".join(checklist_lines)

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

        # 🚨 (loop fix v2) — followup_round NO LONGER incremented here.
        # قبلاً اینجا increment می‌شد، ولی این مسیر از همهٔ verify ها صدا
        # زده می‌شود (manual user, scheduler, sweeper, auto-runner). نتیجه:
        # هر verify partial شمارنده را یک واحد افزایش می‌داد، نه فقط retry
        # های auto-runner. max_retries خیلی سریع می‌رسید و workflow های
        # جاری cancel می‌شدند.
        # حالا increment فقط در `_verify_then_chain` (مسیر auto-runner)
        # اتفاق می‌افتد، در شاخهٔ retry_same. این سمنتیک درست است: followup_round
        # = "چندبار auto-runner این تسک را retry کرده".
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
                # 🔬 (Runtime Verify Stage 1) — AC به ساختار جدید normalize
                try:
                    from .verify_runtime import normalize_ac_list
                    task.acceptance_criteria = normalize_ac_list(extracted_ac)
                except Exception:
                    task.acceptance_criteria = extracted_ac
            # field‌های followup همچنان نگه‌داشته می‌شوند برای backward compat
            # با UI قدیمی (دکمهٔ «اجرای followup»)، ولی prompt اصلی به‌روز است.
            task.followup_prompt = new_prompt
            task.followup_generated_at = now_iso()
            task.followup_target_locations = extracted_locs
            # 🔬 (Runtime Verify Stage 1) — followup AC هم normalize
            try:
                from .verify_runtime import normalize_ac_list
                task.followup_acceptance_criteria = normalize_ac_list(extracted_ac)
            except Exception:
                task.followup_acceptance_criteria = extracted_ac
            # 🚨 (loop fix v2) — followup_round NO LONGER incremented here.
            # increment فقط در `_verify_then_chain` retry_same انجام می‌شود.
            # دلیل: این مسیر از manual/scheduler/sweeper/auto-runner صدا
            # زده می‌شود. اگر اینجا increment کنیم، هر verify partial
            # شمارنده را بالا می‌برد و max_retries زود می‌رسد.
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

        # 🆕 (Phase 2) — پس از اعمال followup روی task.followup_prompt،
        # به‌صورت خودکار آن را به‌عنوان prompt جدید روی task ست می‌کنیم،
        # نسخهٔ قدیمی به prompt_history می‌رود. این کار باعث می‌شود کاربر
        # در دفعهٔ بعدی که verify می‌زند، با همان «پرامپت بروز» کار کند،
        # و دکمهٔ «کپی پرامپت» نسخهٔ به‌روز را در کلیپ‌بورد بگذارد.
        # شکست این مرحله نباید جلوی apply_followup_after_verify را بگیرد.
        try:
            await self.apply_followup_as_new_prompt(
                task_id, reason="verify_followup",
            )
        except Exception as _ae:
            logger.warning(f"apply_followup_as_new_prompt failed for {task_id}: {_ae}")

    # 🆕 (Phase 2) — Prompt versioning + auto-update
    # ====================================================================
    async def apply_followup_as_new_prompt(
        self,
        task_id: str,
        *,
        reason: str = "verify_followup",
    ) -> Dict[str, Any]:
        """نسخهٔ فعلی task.prompt را در prompt_history بایگانی کن و
        task.prompt = task.followup_prompt جدید قرار بده.

        شرایط:
        - task.followup_prompt باید پر باشد (>= 30 char)
        - task.verification_status باید in (partial, not_done, regressed,
          needs_clarification) باشد — نه done، نه pending
        - task.prompt و task.followup_prompt نباید برابر باشند

        عملیات atomic در self._lock:
        1) push نسخهٔ فعلی task.prompt به prompt_history (FIFO، حداکثر ۱۰)
        2) task.prompt = task.followup_prompt (نسخهٔ جدید)
        3) task.followup_prompt = "" (پاک — حالا شده prompt اصلی)
        4) task.updated_at = now_iso()
        5) self._save_tasks()
        """
        allowed_statuses = {"partial", "not_done", "regressed", "needs_clarification"}
        result: Dict[str, Any] = {
            "applied": False, "reason": reason,
            "old_len": 0, "new_len": 0, "history_size": 0,
            "skipped_reason": "",
        }
        async with self._lock:
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task is None:
                result["skipped_reason"] = "task_not_found"
                return result
            old_prompt = (task.prompt or "").strip()
            new_prompt = (task.followup_prompt or "").strip()
            status = (task.verification_status or "").strip()
            if not new_prompt or len(new_prompt) < 30:
                result["skipped_reason"] = "followup_empty_or_too_short"
                return result
            if status not in allowed_statuses:
                result["skipped_reason"] = f"status_not_allowed ({status})"
                return result
            if old_prompt == new_prompt:
                result["skipped_reason"] = "prompt_unchanged"
                return result
            # backward-compat: اگر prompt_history وجود نداشت (داده legacy)
            if not isinstance(task.prompt_history, list):
                task.prompt_history = []
            # 🆕 (Phase 2) — schema هماهنگ با entry های موجود که UI آن‌ها را
            # رندر می‌کند (raw_idea, model_id, generated_at, source). فیلدهای
            # Phase 2 (archived_at, verify_status_at_archive, round) به‌عنوان
            # اضافه نگه‌داری می‌شوند.
            current_round = int(task.followup_round or 0)
            source_label = (
                f"followup_round_{current_round}"
                if reason == "verify_followup" else reason
            )
            entry = {
                "prompt": old_prompt,
                "raw_idea": task.raw_idea or "",
                "model_id": (task.models_used[0] if task.models_used else "") or "",
                "generated_at": task.updated_at or task.created_at or now_iso(),
                "source": source_label,
                # extras
                "archived_at": now_iso(),
                "verify_status_at_archive": status,
                "round": current_round,
            }
            # newest-first (مطابق با کد موجود)
            task.prompt_history.insert(0, entry)
            # FIFO cap = ۱۰ (همان حد existing)
            task.prompt_history = task.prompt_history[:10]
            # اعمال نسخهٔ جدید
            task.prompt = new_prompt
            task.followup_prompt = ""
            task.updated_at = now_iso()
            self._save_tasks()

            result["applied"] = True
            result["old_len"] = len(old_prompt)
            result["new_len"] = len(new_prompt)
            result["history_size"] = len(task.prompt_history)
            logger.info(
                f"prompt_history: task {task_id} prompt updated "
                f"(old={result['old_len']} → new={result['new_len']}, "
                f"history_size={result['history_size']}, reason={reason})"
            )
        return result

    async def revert_prompt_from_history(
        self,
        task_id: str,
        history_index: int,
    ) -> Dict[str, Any]:
        """نسخه‌ای از prompt_history (index) را به‌عنوان prompt فعلی بازنشانی کن.

        ⚠️ ترتیب history همیشه «newest first» است (مطابق با existing code):
        - history_index = 0 یعنی جدیدترین نسخه‌ی بایگانی (یک قدم به عقب).
        - history_index = -1 یعنی قدیمی‌ترین.
        - نسخه‌ی فعلی task.prompt به history منتقل می‌شود (با source="manual_revert").
        - entry هدف از history حذف می‌شود تا تکراری نشود.
        """
        result: Dict[str, Any] = {
            "applied": False, "reverted_to_index": None,
            "history_size_after": 0, "skipped_reason": "",
        }
        async with self._lock:
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task is None:
                result["skipped_reason"] = "task_not_found"
                return result
            if not isinstance(task.prompt_history, list) or not task.prompt_history:
                result["skipped_reason"] = "empty_history"
                return result
            idx = history_index
            n = len(task.prompt_history)
            # support negative index
            if idx < 0:
                idx = n + idx
            if idx < 0 or idx >= n:
                result["skipped_reason"] = f"index_out_of_range ({history_index})"
                return result
            target = task.prompt_history[idx]
            target_prompt = str(target.get("prompt") or "").strip()
            if len(target_prompt) < 30:
                result["skipped_reason"] = "target_prompt_too_short"
                return result
            # archive نسخهٔ فعلی به history (newest-first → insert(0, ...))
            current = (task.prompt or "").strip()
            current_round = int(task.followup_round or 0)
            archive_entry = {
                "prompt": current,
                "raw_idea": task.raw_idea or "",
                "model_id": (task.models_used[0] if task.models_used else "") or "",
                "generated_at": task.updated_at or task.created_at or now_iso(),
                "source": "manual_revert",
                "archived_at": now_iso(),
                "verify_status_at_archive": task.verification_status or "",
                "round": current_round,
            }
            task.prompt_history.insert(0, archive_entry)
            # idx پس از insert یکی شیفت شده (چون عنصر جدید در index 0 آمد)
            # و target حالا در index = idx + 1 است
            try:
                task.prompt_history.pop(idx + 1)
            except IndexError:
                pass
            # cap
            task.prompt_history = task.prompt_history[:10]
            # ست کردن prompt به target
            task.prompt = target_prompt
            task.updated_at = now_iso()
            self._save_tasks()

            result["applied"] = True
            result["reverted_to_index"] = history_index
            result["history_size_after"] = len(task.prompt_history)
        return result

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
        # 🆕 (active vs archived split) — کاربر در dashboard می‌خواست بداند
        # عدد روی کارت «تسک‌ها» چقدر تسک واقعاً در جریان است (نه ارشیوشده‌ها).
        # tasks_count (legacy، کل) را برای سازگاری نگه می‌داریم؛
        # tasks_active_count و tasks_archived_count دو شمارش تفکیک‌شده هستند.
        _archived = sum(1 for t in self.tasks if getattr(t, "archived", False))
        _total = len(self.tasks)
        return {
            "github_token": bool(get_github_token()),
            "render_token": bool(get_render_token()),
            "watched_count": len(self.watched),
            "tasks_count": _total,  # legacy alias: total of everything
            "tasks_total_count": _total,
            "tasks_active_count": _total - _archived,
            "tasks_archived_count": _archived,
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

    async def _maybe_auto_backfill_ac(self) -> None:
        """خودکار backfill AC ها (دکمهٔ زرد) و Phase-3 re-enrich (دکمهٔ بنفش)
        را trigger می‌کند اگر شرایط جمع باشد:

          - settings.auto_backfill_ac_enabled == True
          - یک backfill قبلی در حال اجرا نیست
          - از آخرین run، حداقل auto_backfill_ac_min_hours گذشته
          - حداقل یک AC نیاز به backfill (ac_count > 0) یا upgrade
            (phase3_ac_count > 0) دارد

        نتیجه از طریق همان مسیر معمول (notify_event در پایان
        _run_backfill_ac_classification) به تلگرام می‌رود — هیچ مسیر
        تلگرام جدیدی نیاز نیست.
        """
        if not bool(self.settings.get("auto_backfill_ac_enabled", True)):
            return

        # cooldown
        min_hours = float(self.settings.get("auto_backfill_ac_min_hours") or 6)
        last = self.settings.get("last_auto_backfill_ac_at")
        if last:
            try:
                from datetime import datetime as _dt_cd, timezone as _tz_cd
                last_dt = _dt_cd.fromisoformat(str(last).replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=_tz_cd.utc)
                age_h = (
                    _dt_cd.now(_tz_cd.utc) - last_dt
                ).total_seconds() / 3600.0
                if age_h < min_hours:
                    return
            except Exception:
                pass  # parse failure → run

        # lazy import — جلوگیری از circular import. _BACKFILL_STATE
        # module-level در route file است؛ همچنین خود تابع backfill در آنجاست.
        try:
            from ..api.routes.oversight import (
                _BACKFILL_STATE,
                _run_backfill_ac_classification,
            )
        except Exception as _ie:
            logger.warning(f"auto-backfill: import route module failed: {_ie}")
            return

        if _BACKFILL_STATE.get("running"):
            return  # یک backfill در حال اجراست (دستی یا قبلی)

        # 🚨 (audit fix) — counter قبلاً غلط بود و auto هرگز trigger نمی‌شد.
        # حالا دقیقاً همان منطق /runtime/diagnostics را استفاده می‌کنیم —
        # ui_steps (نه steps)، _ac_already_classified helper، NON_REAL set،
        # و real_count < 1 برای phase3 detection. تمام این موارد در
        # /runtime/diagnostics مشخص است که چه counter ای پشت دکمه‌های UI
        # است. هر تفاوت = silent no-op auto.
        try:
            from .verify_runtime.ac_enricher import _ac_already_classified
        except Exception:
            _ac_already_classified = None  # type: ignore

        _NON_REAL_ACTIONS = {"", "navigate", "screenshot", "wait_for_load"}
        ac_unclassified = 0
        ac_needing_phase3 = 0
        for t in self.tasks:
            if getattr(t, "archived", False):
                continue
            for ac in (getattr(t, "acceptance_criteria", []) or []):
                ac_dict = (
                    ac if isinstance(ac, dict)
                    else {"text": str(ac), "verify_method": "static", "verify_plan": {}}
                )
                # unclassified detection — همان helper diagnostics
                if _ac_already_classified is not None:
                    if not _ac_already_classified(ac_dict):
                        ac_unclassified += 1
                        continue
                else:
                    m_str = str(ac_dict.get("verify_method") or "static").lower()
                    if m_str in ("", "static"):
                        ac_unclassified += 1
                        continue
                # phase3 gap detection — فقط ui_interaction، فقط
                # ui_steps، و real_count < 1
                m = str(ac_dict.get("verify_method") or "static").lower()
                if m != "ui_interaction":
                    continue
                _plan = (ac_dict.get("verify_plan") if isinstance(ac_dict.get("verify_plan"), dict) else {}) or {}
                _steps = _plan.get("ui_steps") or []
                if not isinstance(_steps, list):
                    continue
                _real_count = sum(
                    1 for s in _steps
                    if isinstance(s, dict)
                    and str(s.get("action") or "").lower() not in _NON_REAL_ACTIONS
                )
                if _real_count < 1:
                    ac_needing_phase3 += 1

        if ac_unclassified == 0 and ac_needing_phase3 == 0:
            return  # هیچ کاری لازم نیست

        # ترجیح ارزان‌تر اول: اگر unclassified هست force=False؛ وگرنه force=True
        force = ac_unclassified == 0 and ac_needing_phase3 > 0
        target_count = ac_unclassified if not force else ac_needing_phase3
        logger.info(
            f"auto-backfill-ac: triggering "
            f"({'force/Phase3' if force else 'regular'}) — "
            f"{target_count} AC در صف."
        )

        # state را در همان struct route module ست کن تا /status frontend
        # ببیند و دکمهٔ دستی disable شود.
        from datetime import datetime as _dt_set
        _BACKFILL_STATE["running"] = True
        _BACKFILL_STATE["started_at"] = _dt_set.utcnow().isoformat()
        _BACKFILL_STATE["finished_at"] = None
        _BACKFILL_STATE["current_index"] = 0
        _BACKFILL_STATE["total"] = 0
        _BACKFILL_STATE["summary"] = None
        _BACKFILL_STATE["error"] = None
        _BACKFILL_STATE["force"] = bool(force)
        _BACKFILL_STATE["triggered_by"] = "auto_scheduler"

        # cooldown timestamp ثبت کن (در شروع، نه پایان — تا اگر backfill
        # طولانی شد، tick بعدی دوباره trigger نکند)
        self.settings["last_auto_backfill_ac_at"] = _dt_set.utcnow().isoformat()
        try:
            self._save_settings()
        except Exception:
            pass

        import asyncio as _asyncio_abf
        _asyncio_abf.create_task(
            _run_backfill_ac_classification(None, force=force)
        )

    async def scheduler_tick(self) -> Dict[str, Any]:
        """یک نوبت اجرای scheduler. سه نوع کار: scan، run، verify."""
        now = datetime.now(timezone.utc)
        ran: List[str] = []
        scanned: List[str] = []
        verified: List[str] = []
        max_runs = int(self.settings.get("max_parallel_runs") or 2)

        # 🛡 (audit fix N2) — progress tracker memory cleanup (snapshotهای completed
        # که بیش از 1 ساعت پیش به پایان رسیدند)
        try:
            from .oversight_progress import get_progress_tracker
            await get_progress_tracker().cleanup(older_than_seconds=3600)
        except Exception:
            pass
        # 🛡 compose buffer expired cleanup
        try:
            from .oversight_telegram_compose import get_compose_service
            await get_compose_service().cleanup_expired()
        except Exception:
            pass
        # 🔬 (inspector_probe Phase 1) — TTL پاک‌سازی screenshot های orphan auto-verify
        # هر بار scheduler_tick اجرا می‌شود این هم چک می‌شود؛ هزینه‌اش ناچیز است.
        try:
            import asyncio as _asyncio_lc
            from .oversight_verifier import cleanup_orphan_runtime_screenshots
            await _asyncio_lc.to_thread(cleanup_orphan_runtime_screenshots, 3)
        except Exception:
            pass

        # 🆕 (Auto Backfill AC) — اگر settings فعال است، دکمه‌های زرد/بنفش
        # که قبلاً کاربر دستی می‌زد را خودکار اجرا می‌کنیم. هزینهٔ check
        # ناچیز است (یک شمارش روی task list). در صورت trigger، خود
        # _run_backfill_ac_classification نوتیفیکیشن تلگرام را می‌فرستد.
        try:
            await self._maybe_auto_backfill_ac()
        except Exception as _abe:
            logger.warning(f"auto-backfill-ac check failed: {_abe}")

        # 🆕 (External Pending Verify Sweeper) — هر تیک scheduler چک می‌کنیم
        # که آیا تسک‌هایی هستند که Claude /complete کرد ولی verify-after-complete
        # روی آنها اجرا نشده (مثلاً Render instance خوابیده، background task
        # کشته شده). این sweeper آن تسک‌ها را پیدا و verify-then-chain را
        # دوباره trigger می‌کند تا تسک‌ها گیر نکنند.
        try:
            await self._sweep_pending_external_verifies()
        except Exception as _sw_e:
            logger.warning(f"sweep_pending_external_verifies failed: {_sw_e}")

        # 🆕 🎬 (Inspector Recording Sweeper) — جلسات ضبط که >120m idle بوده‌اند
        # auto-cancel + cleanup disk می‌شوند تا /tmp انباشته نشود.
        try:
            from .inspector_recording_service import get_inspector_recording_service
            _expired = await get_inspector_recording_service().sweep_stale()
            if _expired:
                logger.info(f"inspector_recording sweeper: expired {_expired} stale sessions")
        except Exception as _rec_e:
            logger.warning(f"inspector_recording sweeper failed: {_rec_e}")

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
                                # 🆕 (Smart Task Lifecycle) auto-regenerate
                                # پس از scan، اگر فلگ فعال است، تسک‌های با کیفیت
                                # پایین این پروژه را بازتولید کن (rate-limit 5)
                                if getattr(w, "auto_regenerate_old_prompts", False):
                                    try:
                                        await self.regenerate_low_quality_prompts(
                                            w.id,
                                            max_count=5,
                                            reason="auto_quality_threshold",
                                        )
                                    except Exception as _re:
                                        logger.warning(
                                            f"auto-regen after scan {w.id} failed: {_re}"
                                        )
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
                        # 🆕 (Phase 4) — حالت verify از watched.verify_mode
                        # خوانده می‌شود؛ deep = include_runtime=True (پیش‌فرض)،
                        # fast = include_runtime=False (سریع، بدون probe).
                        _w_verify_mode = (getattr(w, "verify_mode", "deep") or "deep").lower()
                        _include_runtime = (_w_verify_mode != "fast")
                        for t in candidates[:max_runs]:
                            try:
                                from .oversight_verifier import verify_task as _verify_task
                                await _verify_task(
                                    t.id, model_id=None,
                                    triggered_by="scheduler",
                                    include_runtime=_include_runtime,
                                )
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
                    # 🔗 (C7 Bridge Phase 4) — اتصال scheduler به smart-chat
                    # اگر execution_mode == "auto_via_projects_page" یعنی کاربر
                    # خواسته که این تسک از طریق inspector smart-chat اجرا شود.
                    # ping-pong rounds (followup_round > 0) همیشه از طریق
                    # inspector اجرا می‌شوند چون کانتکست تسک حیاتی است.
                    _use_inspector = (
                        t.execution_mode == "auto_via_projects_page"
                        or (t.followup_round or 0) > 0
                    )
                    if _use_inspector:
                        _inspector_result = await self.execute_task_via_inspector(
                            t.id,
                            model_ids=None,
                            followup_only=((t.followup_round or 0) > 0),
                        )
                        if not _inspector_result.get("success"):
                            # fallback به run_task سنتی
                            logger.warning(
                                f"scheduled inspector exec for {t.id} failed: "
                                f"{_inspector_result.get('error')} — fallback to run_task"
                            )
                            await self.run_task(t.id, model_id=None)
                        else:
                            logger.info(
                                f"scheduled inspector exec for {t.id} succeeded "
                                f"(followup_round={t.followup_round or 0})"
                            )
                    else:
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

        # ----- 5) 🆕 (Index Hub) silent refresh پیام ایندکس pin‌شده -----
        # فقط اگر index قبلاً ساخته شده باشد (state در فایل موجود است).
        # rate: هر 60 ثانیه — قابل قبول برای Telegram bot.
        try:
            from .notification_service import notification_service
            await notification_service.refresh_index_silently()
        except Exception as _ie:
            logger.debug(f"index silent refresh skipped: {_ie}")

        # ----- 6) 🆕 (AI Balance — Tile 3) periodic check + alert -----
        # هر 1 ساعت یک بار check_and_notify. self._last_balance_check برای dedup.
        try:
            last_bal = getattr(self, "_last_balance_check", None)
            now_ts = datetime.now(timezone.utc)
            if last_bal is None or (now_ts - last_bal) >= timedelta(hours=1):
                from .ai_balance_service import AIBalanceService
                await AIBalanceService.check_and_notify()
                self._last_balance_check = now_ts
        except Exception as _be:
            logger.debug(f"AI balance check skipped: {_be}")

        # 🔔 (Reminder feature) — یافتن یادآوری‌هایی که موعدشان رسیده و firing
        # اولین/بعدی آن‌ها. خارج از حلقهٔ watched است چون reminders می‌توانند
        # watched_id=None هم داشته باشند (یادآوری شخصی بدون پروژه).
        fired_reminders: List[str] = []
        try:
            due_tasks = [
                t for t in list(self.tasks)
                if t.type == "reminder"
                and t.reminder_state in ("scheduled", "snoozed")
                and t.reminder_at
                and not t.archived
            ]
            for t in due_tasks:
                try:
                    due_dt = datetime.fromisoformat(t.reminder_at.replace("Z", "+00:00"))
                    if due_dt.tzinfo is None:
                        due_dt = due_dt.replace(tzinfo=timezone.utc)
                except Exception as _de:
                    logger.debug(f"reminder {t.id} bad reminder_at: {_de}")
                    continue
                if due_dt > now:
                    continue
                try:
                    from .notification_service import notification_service
                    sent = await notification_service.send_reminder_due(t)
                    if sent:
                        async with self._lock:
                            t.reminder_state = "fired"
                            t.reminder_message_id = sent.get("message_id")
                            t.reminder_history.append({
                                "ts": now.isoformat(),
                                "action": "fired",
                                "message_id": sent.get("message_id"),
                            })
                            t.updated_at = now.isoformat()
                            self._save_tasks()
                        fired_reminders.append(t.id)
                except Exception as _re:
                    logger.warning(f"reminder fire failed for {t.id}: {_re}")
        except Exception as _e:
            logger.warning(f"reminder scheduler block failed: {_e}")

        return {
            "ran": ran,
            "ran_count": len(ran),
            "scanned": scanned,
            "scanned_count": len(scanned),
            "daily_report_sent": daily_sent,
            "verified": verified,
            "verified_count": len(verified),
            "fired_reminders": fired_reminders,
            "fired_reminders_count": len(fired_reminders),
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
