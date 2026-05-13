"""Stage 3e — Runner orchestrator برای probe ها.

این ماژول نقطهٔ ورود اصلی برای اجرای probe ها روی یک task است:

    from .runner import run_probes_for_task
    results = await run_probes_for_task(task, watched, env_config)

Pipeline:
1. AC ها را از task جمع کن (normalize شده از Stage 1)
2. ctx بساز با base_url ها از watched + repo_path + auth
3. برای هر AC، probe مناسب را با semaphore اجرا کن
4. هر probe در timeout خود اجرا می‌شود
5. خروجی List[RuntimeProbeResult] است

این تابع هیچ exception ای بیرون نمی‌اندازد — هر شکست → PROBE_STATUS_ERROR.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .ac_schema import normalize_ac_list
from .base import (
    PROBE_STATUS_ERROR,
    PROBE_STATUS_SKIPPED,
    ProbeContext,
    RuntimeProbeResult,
)
from .api_probe import run_api_probe
from .manual_probe import run_manual_probe
from .static_probe import run_static_probe
from .test_probe import run_test_probe
from .ui_probe import run_ui_probe
from .inspector_probe import run_inspector_probe
from .safety import get_breaker, is_runtime_enabled, is_ui_probe_enabled

logger = logging.getLogger(__name__)


# حداکثر probe های موازی
_DEFAULT_MAX_PARALLEL = 3
# timeout کلی task — اگر همه probe ها با هم بیشتر طول کشیدند، cancel
_DEFAULT_TASK_TIMEOUT_S = 300
# per-probe timeout (فراتر از تنظیم خود probe، یک گارد بالایی)
_PER_PROBE_TIMEOUT_S = 180


def _ac_id_for(ac: Dict[str, Any], index: int) -> str:
    """شناسهٔ پایدار برای یک AC — index + hash text کوتاه."""
    text = (ac.get("text") or "")[:200]
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"ac{index:02d}_{h}"


async def _run_single_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
    semaphore: asyncio.Semaphore,
) -> RuntimeProbeResult:
    """یک AC را با probe مناسب اجرا می‌کند، با semaphore + timeout."""
    method = ac.get("verify_method") or "static"

    # 🛡 (Stage 9) — UI probe در صورت غیرفعال بودن flag، skipped
    if method == "ui_interaction" and not is_ui_probe_enabled():
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=str(ac.get("text") or ""),
            method=method,
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "RUNTIME_VERIFY_UI_ENABLED=false"},
        )

    # 🛡 (Stage 9) — circuit breaker: اگر method open است، skip کن
    breaker = get_breaker()
    if breaker.is_open(method):
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=str(ac.get("text") or ""),
            method=method,
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": f"circuit breaker open for {method}"},
        )

    async with semaphore:
        # synchronous probes را در executor اجرا کن
        result: RuntimeProbeResult
        try:
            if method == "static":
                result = await asyncio.wait_for(
                    asyncio.to_thread(run_static_probe, ac, ctx, ac_id),
                    timeout=_PER_PROBE_TIMEOUT_S,
                )
            elif method == "manual_only":
                result = await asyncio.wait_for(
                    asyncio.to_thread(run_manual_probe, ac, ctx, ac_id),
                    timeout=_PER_PROBE_TIMEOUT_S,
                )
            elif method == "api_response":
                result = await asyncio.wait_for(
                    run_api_probe(ac, ctx, ac_id),
                    timeout=_PER_PROBE_TIMEOUT_S,
                )
            elif method == "backend_test":
                result = await asyncio.wait_for(
                    run_test_probe(ac, ctx, ac_id),
                    timeout=_PER_PROBE_TIMEOUT_S,
                )
            elif method == "ui_interaction":
                # 🔬 (Inspector Probe Phase 1) — اگر verify_plan ui_steps مفصل ندارد،
                # به‌جای ui_probe ساختاریافته، probe سبک inspector را اجرا کن که
                # navigate + click + screenshot + vision + log capture می‌کند و
                # خروجی را در inspector_session ثبت می‌کند.
                plan_dict = ac.get("verify_plan") or {}
                ui_steps_raw = plan_dict.get("ui_steps") or []
                real_steps = (
                    [s for s in ui_steps_raw if isinstance(s, dict)
                     and str(s.get("action") or "") not in ("", "screenshot")]
                    if isinstance(ui_steps_raw, list) else []
                )
                if len(real_steps) >= 3:
                    result = await asyncio.wait_for(
                        run_ui_probe(ac, ctx, ac_id),
                        timeout=_PER_PROBE_TIMEOUT_S,
                    )
                else:
                    result = await asyncio.wait_for(
                        run_inspector_probe(ac, ctx, ac_id),
                        timeout=_PER_PROBE_TIMEOUT_S,
                    )
            else:
                result = RuntimeProbeResult(
                    ac_id=ac_id,
                    ac_text=str(ac.get("text") or ""),
                    method=method,
                    status=PROBE_STATUS_ERROR,
                    evidence={"reason": f"method ناشناخته: {method}"},
                    error_message=f"unknown method: {method}",
                )
        except asyncio.TimeoutError:
            result = RuntimeProbeResult(
                ac_id=ac_id,
                ac_text=str(ac.get("text") or ""),
                method=method,
                status=PROBE_STATUS_ERROR,
                evidence={"reason": f"per-probe timeout ({_PER_PROBE_TIMEOUT_S}s)"},
                error_message="per-probe timeout",
            )
        except Exception as e:
            logger.warning(f"probe {method} crashed for {ac_id}: {e}", exc_info=False)
            result = RuntimeProbeResult(
                ac_id=ac_id,
                ac_text=str(ac.get("text") or ""),
                method=method,
                status=PROBE_STATUS_ERROR,
                evidence={"reason": f"probe crashed: {e}"},
                error_message=str(e)[:300],
            )

        # 🛡 (Stage 9) — circuit breaker را به‌روز کن
        try:
            breaker.record_result(method, result.status)
        except Exception:
            pass
        return result


def build_probe_context(
    *,
    task_id: str,
    run_id: Optional[str] = None,
    repo_path: Optional[str] = None,
    frontend_base_url: Optional[str] = None,
    backend_base_url: Optional[str] = None,
    auth_type: Optional[str] = None,
    auth_value: Optional[str] = None,
    evidence_dir: Optional[str] = None,
    inspector_session_id: Optional[int] = None,
    verify_model_id: Optional[str] = None,
    watched_id: Optional[str] = None,
    storage_state: Optional[Dict[str, Any]] = None,
) -> ProbeContext:
    """helper برای ساخت ProbeContext از پارامترهای ساده."""
    return ProbeContext(
        task_id=task_id,
        run_id=run_id or f"run_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
        repo_path=repo_path,
        frontend_base_url=frontend_base_url,
        backend_base_url=backend_base_url,
        auth_type=auth_type,
        auth_value=auth_value,
        evidence_dir=evidence_dir,
        inspector_session_id=inspector_session_id,
        verify_model_id=verify_model_id,
        watched_id=watched_id,
        storage_state=storage_state,
    )


async def run_probes_for_acs(
    acs: List[Any],
    ctx: ProbeContext,
    *,
    max_parallel: int = _DEFAULT_MAX_PARALLEL,
    task_timeout_s: int = _DEFAULT_TASK_TIMEOUT_S,
) -> List[RuntimeProbeResult]:
    """probe ها را برای یک لیست AC اجرا می‌کند.

    ورودی AC می‌تواند str قدیمی یا dict جدید باشد — normalize می‌شود.
    خروجی List به همان ترتیب AC ها.
    """
    normalized = normalize_ac_list(acs)
    if not normalized:
        return []

    # 🛡 (Stage 9) — اگر runtime layer کلاً disabled است، همه را skip کن
    if not is_runtime_enabled():
        return [
            RuntimeProbeResult(
                ac_id=_ac_id_for(ac, i),
                ac_text=str(ac.get("text") or ""),
                method=str(ac.get("verify_method") or "static"),
                status=PROBE_STATUS_SKIPPED,
                evidence={"reason": "RUNTIME_VERIFY_ENABLED=false"},
            )
            for i, ac in enumerate(normalized)
        ]

    semaphore = asyncio.Semaphore(max_parallel)
    tasks_coros = []
    for i, ac in enumerate(normalized):
        ac_id = _ac_id_for(ac, i)
        tasks_coros.append(_run_single_probe(ac, ctx, ac_id, semaphore))

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks_coros, return_exceptions=False),
            timeout=task_timeout_s,
        )
    except asyncio.TimeoutError:
        logger.warning(f"runner: task timeout ({task_timeout_s}s) — برخی probe ها لغو شدند")
        # هر probe که هنوز در حال اجرا بود را skip محسوب کن — gather lost
        # ما لیست خالی برمی‌گردانیم (یا lite results) — اینجا یک fallback
        results = [
            RuntimeProbeResult(
                ac_id=_ac_id_for(ac, i),
                ac_text=str(ac.get("text") or ""),
                method=str(ac.get("verify_method") or "static"),
                status=PROBE_STATUS_ERROR,
                evidence={"reason": f"task timeout {task_timeout_s}s"},
                error_message="task timeout",
            )
            for i, ac in enumerate(normalized)
        ]
    return list(results)


async def run_probes_for_task(
    task: Any,
    watched: Any = None,
    *,
    repo_path: Optional[str] = None,
    evidence_dir: Optional[str] = None,
    max_parallel: int = _DEFAULT_MAX_PARALLEL,
) -> List[RuntimeProbeResult]:
    """probe ها را برای یک OversightTask اجرا می‌کند.

    base_url ها و auth از `watched` خوانده می‌شوند:
    - watched.frontend_base_url
    - watched.backend_base_url
    - watched.runtime_auth = {type, value}
    """
    acs = list(getattr(task, "acceptance_criteria", []) or [])
    if not acs:
        return []

    # build context از watched
    frontend_url = getattr(watched, "frontend_base_url", None) if watched else None
    backend_url = getattr(watched, "backend_base_url", None) if watched else None
    auth_dict = getattr(watched, "runtime_auth", None) if watched else None
    auth_type = None
    auth_value = None
    if isinstance(auth_dict, dict):
        auth_type = auth_dict.get("type")
        auth_value = auth_dict.get("value")

    ctx = build_probe_context(
        task_id=str(getattr(task, "id", "unknown")),
        repo_path=repo_path,
        frontend_base_url=frontend_url,
        backend_base_url=backend_url,
        auth_type=auth_type,
        auth_value=auth_value,
        evidence_dir=evidence_dir,
    )
    return await run_probes_for_acs(acs, ctx, max_parallel=max_parallel)
