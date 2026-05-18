"""Runtime Verify Layer

این پکیج probes را برای verify فراهم می‌کند:
- static probe (grep code — همان منطق فعلی verifier)
- ui_probe (Playwright — کلیک/ناوبری/screenshot)
- api_probe (HTTP request — status + schema)
- test_probe (pytest subprocess)
- manual_probe (skipped با پیام)

نقطهٔ ورود: `verify_runtime.runner.run_probes_for_task(...)` که برای
هر AC ساختاریافته یک probe مناسب می‌زند و RuntimeProbeResultها را
برمی‌گرداند.
"""

from .ac_schema import (
    AC_METHODS,
    DEFAULT_METHOD,
    normalize_ac,
    normalize_ac_list,
    normalize_task_step,
    normalize_task_steps,
)
from .ac_enricher import enrich_acs_with_verify_plans
from .base import (
    PROBE_STATUS_ERROR,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_SKIPPED,
    PROBE_STATUSES,
    ProbeContext,
    ProbeError,
    RuntimeProbeResult,
)
from .static_probe import run_static_probe
from .manual_probe import run_manual_probe
from .api_probe import run_api_probe
from .test_probe import run_test_probe
from .ui_probe import run_ui_probe
from .runner import (
    build_probe_context,
    run_probes_for_acs,
    run_probes_for_task,
)
from .safety import (
    CircuitBreaker,
    get_breaker,
    is_runtime_enabled,
    is_ui_probe_enabled,
)
# 🔬 (Bug C6 — Verify v6) export نام‌های جدید
from .context_builder import (
    VerifyConfig,
    VerifyContext,
    build_verify_context,
)
from .code_content_searcher import (
    extract_identifiers,
    fetch_file_content,
    grep_token_in_files,
    smart_grep_for_ac,
)
from .iterative_orchestrator import (
    ProbeResult,
    WEIGHTS_BY_PROBE,
    aggregate_verdicts,
    iterative_verify_step,
    _strong_model_judgment,
)
from .ac_cache_service import (
    check_ac_cache,
    compute_files_checksum,
    update_ac_cache,
)

__all__ = [
    "AC_METHODS",
    "DEFAULT_METHOD",
    "normalize_ac",
    "normalize_ac_list",
    "normalize_task_step",
    "normalize_task_steps",
    "enrich_acs_with_verify_plans",
    "PROBE_STATUS_PASSED",
    "PROBE_STATUS_FAILED",
    "PROBE_STATUS_ERROR",
    "PROBE_STATUS_SKIPPED",
    "PROBE_STATUSES",
    "ProbeContext",
    "ProbeError",
    "RuntimeProbeResult",
    "run_static_probe",
    "run_manual_probe",
    "run_api_probe",
    "run_test_probe",
    "run_ui_probe",
    "build_probe_context",
    "run_probes_for_acs",
    "run_probes_for_task",
    "CircuitBreaker",
    "get_breaker",
    "is_runtime_enabled",
    "is_ui_probe_enabled",
    # 🔬 verify v6 exports
    "VerifyConfig",
    "VerifyContext",
    "build_verify_context",
    "extract_identifiers",
    "fetch_file_content",
    "grep_token_in_files",
    "smart_grep_for_ac",
    "ProbeResult",
    "WEIGHTS_BY_PROBE",
    "aggregate_verdicts",
    "iterative_verify_step",
    "_strong_model_judgment",
    "check_ac_cache",
    "compute_files_checksum",
    "update_ac_cache",
]
