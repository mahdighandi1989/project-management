"""Stage 3c — API probe (HTTP request).

برای AC هایی با method=api_response، یک HTTP request به endpoint
داده‌شده می‌زند و status code + شِما را چک می‌کند.

verify_plan schema:
{
  "method": "GET",
  "path": "/api/oversight/status",   # نسبی به backend_base_url
  "headers": null | {...},
  "json_body": null | {...},
  "expected_status": 200,
  "required_fields": ["watched_count", ...],  # JSONPath ساده (top-level keys)
  "json_contains": null | {"key": "value"}   # subset match
}
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .base import (
    PROBE_STATUS_ERROR,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_SKIPPED,
    ProbeContext,
    RuntimeProbeResult,
)

logger = logging.getLogger(__name__)


def _build_auth_headers(ctx: ProbeContext) -> Dict[str, str]:
    """header های authentication را از ctx بساز."""
    headers: Dict[str, str] = {}
    if not ctx.auth_value:
        return headers
    auth_type = (ctx.auth_type or "").lower()
    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {ctx.auth_value}"
    elif auth_type == "cookie":
        headers["Cookie"] = ctx.auth_value
    return headers


def _check_required_fields(data: Any, required: List[str]) -> List[str]:
    """فهرست field های گم‌شده را برمی‌گرداند.

    Support ساده برای dot-path (مثل "user.email") تا یک سطح.
    """
    if not required:
        return []
    missing: List[str] = []
    if not isinstance(data, dict):
        return list(required)
    for field in required:
        parts = str(field).split(".")
        node: Any = data
        ok = True
        for p in parts:
            if not isinstance(node, dict) or p not in node:
                ok = False
                break
            node = node[p]
        if not ok:
            missing.append(field)
    return missing


def _check_json_contains(data: Any, expected: Dict[str, Any]) -> List[str]:
    """فهرست mismatch های subset را برمی‌گرداند."""
    if not expected:
        return []
    mismatches: List[str] = []
    if not isinstance(data, dict):
        return [f"top-level not dict (got {type(data).__name__})"]
    for k, v in expected.items():
        if k not in data:
            mismatches.append(f"missing key '{k}'")
            continue
        if data[k] != v:
            mismatches.append(f"key '{k}': expected {v!r}, got {data[k]!r}")
    return mismatches


async def run_api_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
) -> RuntimeProbeResult:
    """probe API را برای یک AC اجرا می‌کند."""
    start = time.monotonic()
    ac_text = str(ac.get("text") or "")
    plan = ac.get("verify_plan") or {}

    if not ctx.backend_base_url:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="api_response",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "backend_base_url تنظیم نشده"},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    method = str(plan.get("method") or "GET").upper()
    path = str(plan.get("path") or "/")
    if not path.startswith("/"):
        path = "/" + path
    url = ctx.backend_base_url.rstrip("/") + path

    headers = dict(plan.get("headers") or {})
    headers.update(_build_auth_headers(ctx))
    json_body = plan.get("json_body")
    expected_status = int(plan.get("expected_status") or 200)
    required_fields = plan.get("required_fields") or []
    json_contains = plan.get("json_contains") or None

    try:
        import httpx
    except ImportError as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="api_response",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": "httpx not installed"},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e),
        )

    request_kwargs: Dict[str, Any] = {"headers": headers or None}
    if json_body is not None and method in ("POST", "PUT", "PATCH"):
        request_kwargs["json"] = json_body

    try:
        async with httpx.AsyncClient(
            timeout=ctx.api_timeout_s, follow_redirects=True,
        ) as client:
            resp = await client.request(method, url, **request_kwargs)
    except asyncio.TimeoutError:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="api_response",
            status=PROBE_STATUS_FAILED,
            evidence={
                "url": url,
                "method": method,
                "reason": f"timeout after {ctx.api_timeout_s}s",
            },
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=f"timeout after {ctx.api_timeout_s}s",
        )
    except Exception as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="api_response",
            status=PROBE_STATUS_ERROR,
            evidence={"url": url, "method": method, "reason": str(e)[:200]},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e)[:300],
        )

    # response را پارس کن
    response_text = resp.text[:2000]
    try:
        response_json: Any = resp.json()
        json_parsed_ok = True
    except Exception:
        response_json = None
        json_parsed_ok = False

    evidence: Dict[str, Any] = {
        "url": url,
        "method": method,
        "actual_status": resp.status_code,
        "expected_status": expected_status,
        "response_excerpt": response_text[:500],
        "json_parsed": json_parsed_ok,
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    # check status code
    if resp.status_code != expected_status:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="api_response",
            status=PROBE_STATUS_FAILED,
            evidence=evidence,
            duration_ms=duration_ms,
            error_message=f"status {resp.status_code} != {expected_status}",
        )

    # check required fields
    if required_fields:
        if not json_parsed_ok:
            evidence["missing_fields"] = required_fields
            return RuntimeProbeResult(
                ac_id=ac_id,
                ac_text=ac_text,
                method="api_response",
                status=PROBE_STATUS_FAILED,
                evidence=evidence,
                duration_ms=duration_ms,
                error_message="response JSON نبود ولی required_fields داشتیم",
            )
        missing = _check_required_fields(response_json, required_fields)
        if missing:
            evidence["missing_fields"] = missing
            return RuntimeProbeResult(
                ac_id=ac_id,
                ac_text=ac_text,
                method="api_response",
                status=PROBE_STATUS_FAILED,
                evidence=evidence,
                duration_ms=duration_ms,
                error_message=f"missing fields: {', '.join(missing[:5])}",
            )

    # check json_contains
    if json_contains:
        if not json_parsed_ok:
            evidence["json_contains_mismatch"] = "JSON نبود"
            return RuntimeProbeResult(
                ac_id=ac_id,
                ac_text=ac_text,
                method="api_response",
                status=PROBE_STATUS_FAILED,
                evidence=evidence,
                duration_ms=duration_ms,
                error_message="response JSON نبود",
            )
        mismatches = _check_json_contains(response_json, json_contains)
        if mismatches:
            evidence["json_contains_mismatch"] = mismatches
            return RuntimeProbeResult(
                ac_id=ac_id,
                ac_text=ac_text,
                method="api_response",
                status=PROBE_STATUS_FAILED,
                evidence=evidence,
                duration_ms=duration_ms,
                error_message=mismatches[0] if mismatches else "json_contains mismatch",
            )

    # passed
    if json_parsed_ok and isinstance(response_json, dict):
        evidence["response_keys"] = list(response_json.keys())[:20]
    return RuntimeProbeResult(
        ac_id=ac_id,
        ac_text=ac_text,
        method="api_response",
        status=PROBE_STATUS_PASSED,
        evidence=evidence,
        duration_ms=duration_ms,
    )
