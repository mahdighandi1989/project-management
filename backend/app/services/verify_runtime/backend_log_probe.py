"""Phase 4 — Backend Log Probe.

برای AC هایی که از feature backend حرف می‌زنند (نه UI)، به‌جای probe
UI، این probe:

1. Endpoint های ذکر‌شده در AC را استخراج می‌کند (regex)
2. لاگ‌های Render اخیر را فیلتر می‌کند بر اساس:
   - نام فایل‌های target_files تسک
   - endpoint های استخراج‌شده
   - keyword های مهم AC
3. AI بررسی می‌کند verdict:
   - "deployed_working" — feature deploy شده و call می‌شود بدون خطا
   - "deployed_with_errors" — deploy شده ولی exception/error
   - "deployed_not_called" — deploy شده ولی هیچ call ای نیست
   - "not_deployed" — هیچ نشانه‌ای از این کد در لاگ‌ها نیست
   - "unclear" — اطلاعات کافی نیست

API: run_backend_log_probe(ac, ctx, ac_id, task)
خروجی: RuntimeProbeResult با method="backend_log"
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .base import (
    PROBE_STATUS_ERROR, PROBE_STATUS_FAILED, PROBE_STATUS_PASSED,
    PROBE_STATUS_SKIPPED,
    ProbeContext, RuntimeProbeResult,
)

logger = logging.getLogger(__name__)

# محدودیت‌ها
_MAX_LOGS_TO_FETCH = 100
_LOG_WINDOW_HOURS = 24
_AI_TIMEOUT_S = 20
_MAX_PATCH_CHARS = 800


def _extract_endpoints_from_text(text: str) -> List[Dict[str, str]]:
    """endpoint های HTTP را از متن AC یا scope استخراج کن.

    الگوها:
      GET /api/foo
      POST /api/bar
      DELETE /api/baz/{id}
      `/api/x` (بدون method)
    """
    out: List[Dict[str, str]] = []
    if not text:
        return out
    # method + path
    for m in re.finditer(
        r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[a-zA-Z0-9_/{}.-]+)",
        text,
    ):
        out.append({"method": m.group(1).upper(), "path": m.group(2)})
    # path تنها (در `...` یا inline)
    if not out:
        for m in re.finditer(r"`(/api/[a-zA-Z0-9_/{}.-]+)`", text):
            out.append({"method": "*", "path": m.group(1)})
    return out


def _extract_python_symbols(text: str) -> List[str]:
    """تابع/کلاس‌های Python از متن استخراج کن (مثل `traverse()`, `DebateAttachment`)."""
    out: List[str] = []
    if not text:
        return out
    # snake_case function
    for m in re.finditer(r"\b([a-z_][a-z0-9_]+)\s*\(\)", text):
        out.append(m.group(1))
    # CamelCase class
    for m in re.finditer(r"\b([A-Z][a-zA-Z0-9]+)\b", text):
        out.append(m.group(1))
    # dedup با حفظ ترتیب
    seen = set()
    result = []
    for s in out:
        if s not in seen and len(s) >= 3:
            seen.add(s)
            result.append(s)
    return result[:15]


async def _fetch_relevant_logs(
    target_files: List[str],
    endpoints: List[Dict[str, str]],
    symbols: List[str],
    window_hours: int = _LOG_WINDOW_HOURS,
) -> List[Dict[str, Any]]:
    """لاگ‌های Render فیلتر شده بر اساس signal های تسک."""
    try:
        from ...core.database import SessionLocal
        from ...models.render_log import RenderLog
    except Exception as e:
        logger.debug(f"backend_log_probe: model import failed: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    # نام فایل‌های پایه (مثل rule_routing_diagram.py از مسیر کامل)
    file_basenames = [
        str(f).rsplit("/", 1)[-1].split(".", 1)[0]
        for f in target_files if f
    ]
    file_basenames = [b for b in file_basenames if len(b) >= 4]

    def _q() -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            # query کل پنجره زمانی، بعد فیلتر در Python
            # (SQL LIKE با چندتا keyword پیچیده است)
            rows = (
                db.query(RenderLog)
                .filter(RenderLog.timestamp >= cutoff)
                .order_by(RenderLog.timestamp.desc())
                .limit(_MAX_LOGS_TO_FETCH * 3)
                .all()
            )
            keywords = (
                file_basenames
                + [s for s in symbols if len(s) >= 4]
                + [e["path"] for e in endpoints]
            )
            keywords_low = [k.lower() for k in keywords if k]
            filtered: List[Dict[str, Any]] = []
            for r in rows:
                msg_low = (r.message or "").lower()
                # match: حداقل یک keyword
                if not keywords_low or any(k in msg_low for k in keywords_low):
                    filtered.append({
                        "level": r.level,
                        "message": (r.message or "")[:600],
                        "service_id": r.service_id,
                        "service_name": r.service_name,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    })
                if len(filtered) >= _MAX_LOGS_TO_FETCH:
                    break
            return filtered
        except Exception as e:
            logger.debug(f"backend_log_probe: query failed: {e}")
            return []
        finally:
            db.close()

    rows = await asyncio.to_thread(_q)
    return rows


async def _ai_analyze_backend_logs(
    ac_text: str,
    target_files: List[str],
    endpoints: List[Dict[str, str]],
    symbols: List[str],
    logs: List[Dict[str, Any]],
    verify_model_id: Optional[str],
) -> Dict[str, Any]:
    """AI verdict بر اساس signal های جمع‌آوری شده.

    Returns:
      {verdict, reason, evidence_lines}
      verdict ∈ {deployed_working, deployed_with_errors,
                 deployed_not_called, not_deployed, unclear}
    """
    none_result = {
        "verdict": "unclear",
        "reason": "AI تحلیل ناموفق یا context کافی نبود",
        "evidence_lines": [],
    }

    try:
        from ..ai_manager import get_ai_manager
        from ..ai_base import Message
    except Exception:
        return none_result

    if not verify_model_id:
        try:
            from ...core.models_registry import DEFAULT_EXTRACTION_MODEL_ID
            verify_model_id = DEFAULT_EXTRACTION_MODEL_ID
        except Exception:
            pass
    if not verify_model_id:
        return none_result

    target_files_text = ", ".join(target_files[:10]) or "(none)"
    endpoints_text = (
        ", ".join(f"{e['method']} {e['path']}" for e in endpoints[:8])
        or "(none extracted)"
    )
    symbols_text = ", ".join(symbols[:10]) or "(none)"

    logs_block = "\n".join(
        f"[{r.get('level', '?').upper()}] "
        f"{(r.get('timestamp') or '')[:19]} "
        f"({r.get('service_id', '?')[:12]}): "
        f"{(r.get('message') or '')[:400]}"
        for r in logs[:50]
    ) or "(no relevant logs found)"

    prompt = (
        "تو یک مهندس DevOps هستی. وظیفه‌ات تشخیص این است که آیا یک ویژگی\n"
        "backend (که در AC تعریف شده) واقعاً deploy شده و در سرور Render\n"
        "کار می‌کند یا نه. این کار از طریق تحلیل لاگ‌های اخیر انجام می‌شود.\n\n"
        f"📋 AC مورد بررسی:\n{ac_text}\n\n"
        f"📁 فایل‌های هدف: {target_files_text}\n"
        f"📌 endpoint های استخراج‌شده از AC: {endpoints_text}\n"
        f"🔤 symbols (تابع/کلاس) استخراج‌شده: {symbols_text}\n\n"
        f"📊 لاگ‌های Render اخیر (فیلتر شده):\n{logs_block}\n\n"
        "⚠️ راهنما برای verdict:\n"
        "- 'deployed_working': لاگ‌ها نشان می‌دهند endpoint یا تابع call شده\n"
        "  و response/result بدون خطا بوده.\n"
        "- 'deployed_with_errors': call شده ولی exception/error/warn ثبت شده.\n"
        "- 'deployed_not_called': شاید deploy شده ولی هیچ call ای دیده نمی‌شود\n"
        "  (مثلاً تابع جدید ولی هیچ‌کس استفاده نمی‌کند).\n"
        "- 'not_deployed': هیچ نشانه‌ای از این کد در لاگ‌ها نیست — احتمالاً\n"
        "  این feature هنوز deploy نشده.\n"
        "- 'unclear': لاگ‌ها مرتبط نیستند یا اطلاعات کافی نیست.\n\n"
        "⚠️ مهم: فقط بر اساس لاگ‌های ارائه‌شده تصمیم بگیر، حدس نزن.\n\n"
        "خروجی JSON خالص:\n"
        "{\n"
        '  "verdict": "deployed_working|deployed_with_errors|'
        'deployed_not_called|not_deployed|unclear",\n'
        '  "reason": "یک جمله توضیح چرا این verdict",\n'
        '  "evidence_lines": ["خط لاگ کلیدی ۱", "خط لاگ کلیدی ۲"]\n'
        "}"
    )

    try:
        mgr = get_ai_manager()
        resp = await asyncio.wait_for(
            mgr.generate(
                model_id=verify_model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=1500,
                temperature=0.1,
                allow_fallback=True,
            ),
            timeout=_AI_TIMEOUT_S,
        )
        raw = (resp.content or "").strip()
    except asyncio.TimeoutError:
        return none_result
    except Exception as e:
        logger.warning(f"backend_log_probe AI failed: {e}")
        return none_result

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return none_result
    try:
        data = json.loads(raw[start:end + 1])
    except Exception:
        return none_result

    verdict = str(data.get("verdict") or "unclear").strip().lower()
    valid = {"deployed_working", "deployed_with_errors",
             "deployed_not_called", "not_deployed", "unclear"}
    if verdict not in valid:
        verdict = "unclear"
    return {
        "verdict": verdict,
        "reason": str(data.get("reason") or "")[:500],
        "evidence_lines": [
            str(x)[:300] for x in (data.get("evidence_lines") or [])[:5]
        ],
    }


async def run_backend_log_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
    task: Any,
) -> RuntimeProbeResult:
    """probe اصلی — برای AC هایی که backend-focused هستند.

    این probe هیچ exception ای بیرون نمی‌اندازد.
    """
    start = time.monotonic()
    ac_text = str(ac.get("text") if isinstance(ac, dict) else ac).strip()

    # signal extraction
    full_text = ac_text + " " + " ".join(
        f"{s.get('title', '')} {s.get('scope', '')}"
        for s in (getattr(task, "task_steps", None) or [])
        if isinstance(s, dict)
    )
    endpoints = _extract_endpoints_from_text(full_text)
    symbols = _extract_python_symbols(full_text)
    target_files = list(getattr(task, "target_files", None) or [])

    # fetch logs
    logs = await _fetch_relevant_logs(
        target_files=target_files,
        endpoints=endpoints,
        symbols=symbols,
    )

    if not logs:
        return RuntimeProbeResult(
            ac_id=ac_id, ac_text=ac_text, method="backend_log",
            status=PROBE_STATUS_SKIPPED,
            evidence={
                "reason": "no relevant Render logs found in last 24h",
                "endpoints": endpoints,
                "symbols": symbols,
                "target_files_basenames": [
                    str(f).rsplit("/", 1)[-1] for f in target_files[:5]
                ],
                "probe_type": "backend_log_phase4",
            },
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    # AI verdict
    verdict_result = await _ai_analyze_backend_logs(
        ac_text=ac_text,
        target_files=target_files,
        endpoints=endpoints,
        symbols=symbols,
        logs=logs,
        verify_model_id=ctx.verify_model_id,
    )
    verdict = verdict_result.get("verdict", "unclear")

    # نگاشت verdict → probe status
    status_map = {
        "deployed_working": PROBE_STATUS_PASSED,
        "deployed_with_errors": PROBE_STATUS_FAILED,
        "deployed_not_called": PROBE_STATUS_FAILED,
        "not_deployed": PROBE_STATUS_FAILED,
        "unclear": PROBE_STATUS_SKIPPED,
    }
    status = status_map.get(verdict, PROBE_STATUS_SKIPPED)

    return RuntimeProbeResult(
        ac_id=ac_id, ac_text=ac_text, method="backend_log",
        status=status,
        evidence={
            "verdict": verdict,
            "reason": verdict_result.get("reason", ""),
            "evidence_lines": verdict_result.get("evidence_lines", []),
            "endpoints_extracted": endpoints,
            "symbols_extracted": symbols,
            "log_count": len(logs),
            "log_window_hours": _LOG_WINDOW_HOURS,
            "probe_type": "backend_log_phase4",
        },
        duration_ms=int((time.monotonic() - start) * 1000),
    )
