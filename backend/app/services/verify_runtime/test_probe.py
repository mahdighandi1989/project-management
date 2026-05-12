"""Stage 3d — Backend test probe (pytest subprocess).

برای AC هایی با method=backend_test، یک pytest با node id داده‌شده
در subprocess اجرا می‌کند.

verify_plan schema:
{
  "test_node": "tests/test_foo.py::test_bar",
  "timeout_seconds": 60
}
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .base import (
    PROBE_STATUS_ERROR,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_SKIPPED,
    ProbeContext,
    RuntimeProbeResult,
)

logger = logging.getLogger(__name__)


async def run_test_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
) -> RuntimeProbeResult:
    """probe pytest را در subprocess اجرا می‌کند.

    - subprocess: `python -m pytest <node> -v --tb=short --no-header`
    - timeout: از plan یا ctx.test_timeout_s
    - cwd: ctx.repo_path یا cwd فعلی
    - stdout/stderr capture می‌شوند و در evidence قرار می‌گیرند
    """
    start = time.monotonic()
    ac_text = str(ac.get("text") or "")
    plan = ac.get("verify_plan") or {}
    test_node = str(plan.get("test_node") or "").strip()

    if not test_node:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "test_node در verify_plan نیست"},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    timeout = int(plan.get("timeout_seconds") or ctx.test_timeout_s)
    cwd = ctx.repo_path or None
    if cwd and not Path(cwd).is_dir():
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": "repo_path موجود نیست", "cwd": cwd},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=f"cwd not found: {cwd}",
        )

    # subprocess
    cmd = [
        "python", "-m", "pytest", test_node,
        "-v", "--tb=short", "--no-header", "--color=no",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": f"python/pytest در PATH نیست: {e}"},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e),
        )
    except Exception as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": f"subprocess spawn failed: {e}"},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e),
        )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_FAILED,
            evidence={
                "test_node": test_node,
                "reason": f"timeout after {timeout}s",
            },
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=f"timeout after {timeout}s",
        )

    stdout_text = (stdout or b"").decode("utf-8", errors="replace")
    stderr_text = (stderr or b"").decode("utf-8", errors="replace")
    duration_ms = int((time.monotonic() - start) * 1000)

    evidence: Dict[str, Any] = {
        "test_node": test_node,
        "return_code": proc.returncode,
        "stdout_excerpt": stdout_text[-3000:],
        "stderr_excerpt": stderr_text[-1500:] if stderr_text else "",
    }

    # pytest return codes: 0=all passed, 1=tests failed, 2=internal error,
    # 3=test collection error, 4=usage error, 5=no tests collected
    rc = proc.returncode if proc.returncode is not None else -1
    if rc == 0:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_PASSED,
            evidence=evidence,
            duration_ms=duration_ms,
        )
    if rc == 5:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_SKIPPED,
            evidence={**evidence, "reason": "no tests collected"},
            duration_ms=duration_ms,
            error_message="no tests collected",
        )
    if rc in (2, 3, 4):
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="backend_test",
            status=PROBE_STATUS_ERROR,
            evidence=evidence,
            duration_ms=duration_ms,
            error_message=f"pytest internal error (rc={rc})",
        )
    # rc == 1 یا غیره → failed
    return RuntimeProbeResult(
        ac_id=ac_id,
        ac_text=ac_text,
        method="backend_test",
        status=PROBE_STATUS_FAILED,
        evidence=evidence,
        duration_ms=duration_ms,
        error_message=f"pytest failed (rc={rc})",
    )
