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
]
