"""Behavioral Probe Layer — wrapper/alias module برای verify_runtime.

این فایل یک لایهٔ معماری شفاف روی probe های موجود فراهم می‌کند:
  - BehavioralProbeOrchestrator: نقطهٔ ورود واحد برای اجرای probes
  - BehavioralProbeResult: dataclass خروجی هر probe
  - UIProbe / APIProbe / TestProbe: کلاس‌های wrapper روی توابع موجود

این کلاس‌ها alias/wrapper روی پیاده‌سازی‌های فعلی هستند:
  - BehavioralProbeOrchestrator → iterative_orchestrator (iterative_verify_step, aggregate_verdicts)
  - UIProbe.capture_screenshot → ui_probe._take_screenshot
  - APIProbe.execute_http_probe → api_probe.run_api_probe
  - TestProbe.run_pytest_probe → test_probe.run_test_probe

هیچ منطق جدیدی اضافه نمی‌کند — فقط interface object-oriented برای کسانی
که این سبک را می‌پسندند.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import ProbeContext, RuntimeProbeResult
from .iterative_orchestrator import (
    ProbeResult,
    aggregate_verdicts,
    iterative_verify_step,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BehavioralProbeResult — dataclass استاندارد خروجی هر probe
# ---------------------------------------------------------------------------


@dataclass
class BehavioralProbeResult:
    """نتیجهٔ یک behavioral probe.

    این dataclass interface استاندارد است که توسط BehavioralProbeOrchestrator
    و کلاس‌های Probe زیر برگردانده می‌شود.

    معادل ProbeResult موجود در iterative_orchestrator (ولی با فیلدهای
    مشخصاً documented برای layer جدید).
    """
    ac_id: str
    probe_type: str  # "ui" | "api" | "test" | "static" | "manual" | "inspector" | "aggregate"
    evidence: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error_message: Optional[str] = None
    # فیلدهای اضافی برای سازگاری با ProbeResult قدیمی
    verdict: str = "unclear"  # "done" | "partial" | "not_done" | "unclear"
    confidence: float = 0.0
    elapsed_ms: int = 0

    @classmethod
    def from_runtime_probe_result(
        cls, r: RuntimeProbeResult, ac_id: Optional[str] = None,
    ) -> "BehavioralProbeResult":
        """تبدیل RuntimeProbeResult موجود به BehavioralProbeResult."""
        success = r.status == "passed"
        verdict = "done" if success else (
            "not_done" if r.status == "failed" else "unclear"
        )
        return cls(
            ac_id=ac_id or getattr(r, "ac_id", "") or "",
            probe_type=getattr(r, "method", "") or "",
            evidence=getattr(r, "evidence", None) or {},
            success=success,
            error_message=getattr(r, "error_message", None),
            verdict=verdict,
            confidence=1.0 if success else (0.0 if r.status == "failed" else 0.5),
            elapsed_ms=int(getattr(r, "duration_ms", 0) or 0),
        )

    @classmethod
    def from_probe_result(
        cls, p: ProbeResult, ac_id: str = "", probe_type: str = "",
    ) -> "BehavioralProbeResult":
        """تبدیل ProbeResult (iterative_orchestrator) به BehavioralProbeResult."""
        success = p.verdict == "done"
        return cls(
            ac_id=ac_id,
            probe_type=probe_type or p.probe_name,
            evidence={"evidence_lines": list(p.evidence or [])},
            success=success,
            error_message=p.error,
            verdict=p.verdict,
            confidence=p.confidence,
            elapsed_ms=p.elapsed_ms,
        )


# ---------------------------------------------------------------------------
# UIProbe / APIProbe / TestProbe — class wrappers روی توابع موجود
# ---------------------------------------------------------------------------


class UIProbe:
    """Wrapper class روی ui_probe.run_ui_probe.

    interface object-oriented برای UI probing. متد اصلی:
      - run(ac, ctx) → BehavioralProbeResult
      - capture_screenshot(page, evidence_path, label) → screenshot path
    """

    def __init__(self, ctx: Optional[ProbeContext] = None) -> None:
        self.ctx = ctx

    async def run(
        self,
        ac: Dict[str, Any],
        ctx: Optional[ProbeContext] = None,
        ac_id: str = "",
    ) -> BehavioralProbeResult:
        from .ui_probe import run_ui_probe
        result = await run_ui_probe(ac, ctx or self.ctx, ac_id)
        return BehavioralProbeResult.from_runtime_probe_result(result, ac_id=ac_id)

    @staticmethod
    async def capture_screenshot(
        page: Any,
        evidence_path: Optional[Any] = None,
        label: str = "screenshot",
    ) -> Optional[str]:
        """Screenshot از page Playwright — wrapper روی _take_screenshot.

        Returns: مسیر فایل ذخیره‌شده، یا None در صورت خطا.
        """
        try:
            from .ui_probe import _take_screenshot
            return await _take_screenshot(page, evidence_path, label)
        except Exception as e:
            logger.debug(f"UIProbe.capture_screenshot failed: {e}")
            return None


class APIProbe:
    """Wrapper class روی api_probe.run_api_probe.

    متد اصلی:
      - run(ac, ctx) → BehavioralProbeResult
      - execute_http_probe(method, url, ...) → response dict
    """

    def __init__(self, ctx: Optional[ProbeContext] = None) -> None:
        self.ctx = ctx

    async def run(
        self,
        ac: Dict[str, Any],
        ctx: Optional[ProbeContext] = None,
        ac_id: str = "",
    ) -> BehavioralProbeResult:
        from .api_probe import run_api_probe
        result = await run_api_probe(ac, ctx or self.ctx, ac_id)
        return BehavioralProbeResult.from_runtime_probe_result(result, ac_id=ac_id)

    @staticmethod
    async def execute_http_probe(
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        timeout_s: int = 10,
    ) -> Dict[str, Any]:
        """یک HTTP request مستقل بزن و response را به‌صورت dict برگردان.

        Returns: {status: int, headers: dict, body: str|dict, error: str|None}
        """
        try:
            import aiohttp
        except ImportError as e:
            return {"status": 0, "headers": {}, "body": None, "error": f"aiohttp not installed: {e}"}

        try:
            _to = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=_to) as session:
                async with session.request(
                    method.upper(),
                    url,
                    headers=headers or {},
                    json=body if isinstance(body, (dict, list)) else None,
                    data=body if isinstance(body, (str, bytes)) else None,
                ) as resp:
                    _status = resp.status
                    _hdrs = dict(resp.headers)
                    _ct = (_hdrs.get("Content-Type") or "").lower()
                    if "application/json" in _ct:
                        try:
                            _body = await resp.json()
                        except Exception:
                            _body = await resp.text()
                    else:
                        _body = await resp.text()
                    return {
                        "status": _status,
                        "headers": _hdrs,
                        "body": _body,
                        "error": None,
                    }
        except Exception as e:
            return {"status": 0, "headers": {}, "body": None, "error": str(e)}


class TestProbe:
    """Wrapper class روی test_probe.run_test_probe.

    متد اصلی:
      - run(ac, ctx) → BehavioralProbeResult
      - run_pytest_probe(test_path, marker, ...) → output dict
    """

    def __init__(self, ctx: Optional[ProbeContext] = None) -> None:
        self.ctx = ctx

    async def run(
        self,
        ac: Dict[str, Any],
        ctx: Optional[ProbeContext] = None,
        ac_id: str = "",
    ) -> BehavioralProbeResult:
        from .test_probe import run_test_probe
        result = await run_test_probe(ac, ctx or self.ctx, ac_id)
        return BehavioralProbeResult.from_runtime_probe_result(result, ac_id=ac_id)

    @staticmethod
    async def run_pytest_probe(
        test_path: Optional[str] = None,
        marker: Optional[str] = None,
        *,
        repo_path: Optional[str] = None,
        timeout_s: int = 240,
    ) -> Dict[str, Any]:
        """pytest را با marker اجرا کن و output را capture کن.

        Args:
          test_path: مسیر فایل تست (یا دایرکتوری)
          marker: مارکر pytest (مثل "smoke" یا "verify")
          repo_path: ریشهٔ پروژه برای اجرای pytest
          timeout_s: timeout کلی

        Returns: {success: bool, returncode: int, stdout: str, stderr: str, error: str|None}
        """
        import asyncio
        import os
        import shlex

        args: List[str] = ["pytest", "-q"]
        if marker:
            args.extend(["-m", marker])
        if test_path:
            args.append(test_path)

        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")

        cwd = repo_path or os.getcwd()

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": "",
                    "error": f"pytest timeout after {timeout_s}s",
                }
            rc = proc.returncode if proc.returncode is not None else -1
            stdout = (stdout_b or b"").decode("utf-8", errors="replace")
            stderr = (stderr_b or b"").decode("utf-8", errors="replace")
            return {
                "success": rc == 0,
                "returncode": rc,
                "stdout": stdout[-8000:],
                "stderr": stderr[-4000:],
                "error": None,
            }
        except FileNotFoundError as e:
            return {
                "success": False, "returncode": -1, "stdout": "", "stderr": "",
                "error": f"pytest not installed: {e}",
            }
        except Exception as e:
            return {
                "success": False, "returncode": -1, "stdout": "", "stderr": "",
                "error": str(e),
            }


# ---------------------------------------------------------------------------
# BehavioralProbeOrchestrator — نقطهٔ ورود واحد
# ---------------------------------------------------------------------------


class BehavioralProbeOrchestrator:
    """ارکستراتور behavioral probes — wrapper روی iterative_orchestrator.

    این کلاس interface object-oriented برای اجرای probe ها فراهم می‌کند.
    داخل از iterative_verify_step و aggregate_verdicts استفاده می‌کند که
    منطق اصلی verify v6/v7 هستند (شامل task_type classification،
    contradiction resolution، step_summary trace).

    Usage:
        orch = BehavioralProbeOrchestrator(context=verify_ctx)
        result = await orch.run_step(ac_dict)
        # result is BehavioralProbeResult با verdict نهایی aggregate
    """

    def __init__(self, context: Optional[Any] = None) -> None:
        """
        Args:
          context: VerifyContext از verify_runtime.context_builder
        """
        self.context = context
        self.ui_probe = UIProbe()
        self.api_probe = APIProbe()
        self.test_probe = TestProbe()

    async def run_step(
        self,
        step: Dict[str, Any],
        *,
        max_iterations: int = 3,
    ) -> Tuple[BehavioralProbeResult, List[BehavioralProbeResult]]:
        """اجرای iterative یک step/AC با ۳ سطح escalation.

        خروجی: (final_aggregated, all_iteration_results)
        """
        if self.context is None:
            raise ValueError(
                "BehavioralProbeOrchestrator.run_step needs context (VerifyContext)"
            )
        final_pr, all_pr = await iterative_verify_step(
            step, self.context, max_iterations=max_iterations,
        )
        ac_id = str(step.get("id", "") or step.get("text", "")[:50])
        final_bpr = BehavioralProbeResult.from_probe_result(
            final_pr, ac_id=ac_id, probe_type="aggregate",
        )
        all_bpr = [
            BehavioralProbeResult.from_probe_result(p, ac_id=ac_id, probe_type=p.probe_name)
            for p in all_pr
        ]
        return final_bpr, all_bpr

    def aggregate(
        self,
        results: List[BehavioralProbeResult],
    ) -> BehavioralProbeResult:
        """رأی‌گیری وزنی روی چند BehavioralProbeResult.

        داخل به ProbeResult تبدیل و از aggregate_verdicts استفاده می‌کند.
        """
        as_probe_results = [
            ProbeResult(
                probe_name=r.probe_type,
                verdict=r.verdict,
                confidence=r.confidence,
                evidence=list((r.evidence or {}).get("evidence_lines", [])),
                error=r.error_message,
                elapsed_ms=r.elapsed_ms,
            )
            for r in results
        ]
        agg = aggregate_verdicts(as_probe_results)
        return BehavioralProbeResult.from_probe_result(
            agg, ac_id="aggregate", probe_type="aggregate",
        )


__all__ = [
    "BehavioralProbeResult",
    "BehavioralProbeOrchestrator",
    "UIProbe",
    "APIProbe",
    "TestProbe",
]
