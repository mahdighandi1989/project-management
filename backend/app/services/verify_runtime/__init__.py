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

__all__ = [
    "AC_METHODS",
    "DEFAULT_METHOD",
    "normalize_ac",
    "normalize_ac_list",
    "normalize_task_step",
    "normalize_task_steps",
]
