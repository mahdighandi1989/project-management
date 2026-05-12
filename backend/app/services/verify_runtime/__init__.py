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
]
