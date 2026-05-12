"""ساختار AC (Acceptance Criterion) و normalize.

AC ساختاریافته:
{
  "text": str,                 # متن AC (verbatim از پرامپت)
  "verify_method": str,        # یکی از AC_METHODS
  "verify_plan": Dict | None,  # ساختار وابسته به method (در ادامه)
  "evidence_history": List[Dict],  # هر run قبلی: {run_id, ts, status, summary}
  "last_status": str | None,   # passed | failed | error | skipped | None
  "last_run_at": str | None,   # ISO datetime
}

verify_plan schema (وابسته به method):

method="static":
  {
    "grep_patterns": [str, ...],   # patternهایی که باید در کد موجود باشند
    "files_hint": [str, ...],      # فایل‌های احتمالی (راهنمایی، نه الزام)
  }

method="ui_interaction":
  {
    "base": "frontend" | "backend",  # کدام base_url استفاده شود
    "ui_steps": [
      {"action": "navigate", "url": "/oversight"},
      {"action": "wait_for_load_state", "state": "networkidle"},
      {"action": "click", "selector": "[data-testid='btn']"},
      {"action": "fill", "selector": "input[name=x]", "value": "..."},
      {"action": "wait_for_selector", "selector": "...", "timeout_ms": 3000},
      {"action": "assert_visible", "selector": "..."},
      {"action": "assert_text", "selector": "...", "contains": "..."},
      {"action": "assert_url", "contains": "/dashboard"},
      {"action": "screenshot", "label": "after_click"},
    ]
  }

method="api_response":
  {
    "method": "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    "path": "/api/oversight/status",   # نسبی به backend_base_url
    "headers": {"...": "..."} | None,
    "json_body": {...} | None,
    "expected_status": 200,
    "required_fields": ["watched_count", "tasks_count"],  # JSONPath ساده
    "json_contains": {"key": "value"} | None,
  }

method="backend_test":
  {
    "test_node": "tests/test_foo.py::test_bar",   # nodeid pytest
    "timeout_seconds": 60,
  }

method="manual_only":
  {
    "reason": "verify باید توسط بازبینی انسانی انجام شود"
  }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

AC_METHODS = (
    "static",
    "ui_interaction",
    "api_response",
    "backend_test",
    "manual_only",
)

DEFAULT_METHOD = "static"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_method(val: Any) -> str:
    s = (str(val) if val is not None else "").strip().lower()
    return s if s in AC_METHODS else DEFAULT_METHOD


def _default_plan_for_method(method: str) -> Dict[str, Any]:
    """plan خالی ولی valid برای هر method (در صورت نبود)."""
    if method == "static":
        return {"grep_patterns": [], "files_hint": []}
    if method == "ui_interaction":
        return {"base": "frontend", "ui_steps": []}
    if method == "api_response":
        return {
            "method": "GET",
            "path": "/",
            "headers": None,
            "json_body": None,
            "expected_status": 200,
            "required_fields": [],
            "json_contains": None,
        }
    if method == "backend_test":
        return {"test_node": "", "timeout_seconds": 60}
    if method == "manual_only":
        return {"reason": "نیاز به بازبینی دستی"}
    return {}


def normalize_ac(ac: Any) -> Dict[str, Any]:
    """یک AC را به ساختار استاندارد تبدیل می‌کند.

    ورودی می‌تواند:
    - str قدیمی: یک AC ساده — `verify_method="static"` گرفته می‌شود
    - dict جدید با فیلدهای موجود: همان را normalize و فیلدهای کم را پر می‌کند
    - چیز دیگر (None/int/...): به یک AC با `text=str(input)` تبدیل می‌شود
    """
    if isinstance(ac, dict):
        text = str(ac.get("text") or ac.get("description") or "").strip()
        method = _coerce_method(ac.get("verify_method"))
        plan = ac.get("verify_plan")
        if not isinstance(plan, dict):
            plan = _default_plan_for_method(method)
        else:
            # merge با defaults تا فیلدهای الزامی همیشه باشند
            base = _default_plan_for_method(method)
            base.update(plan)
            plan = base
        history = ac.get("evidence_history") or []
        if not isinstance(history, list):
            history = []
        return {
            "text": text,
            "verify_method": method,
            "verify_plan": plan,
            "evidence_history": history[-20:],
            "last_status": ac.get("last_status"),
            "last_run_at": ac.get("last_run_at"),
        }

    if isinstance(ac, str):
        return {
            "text": ac.strip(),
            "verify_method": DEFAULT_METHOD,
            "verify_plan": _default_plan_for_method(DEFAULT_METHOD),
            "evidence_history": [],
            "last_status": None,
            "last_run_at": None,
        }

    return {
        "text": str(ac).strip() if ac is not None else "",
        "verify_method": DEFAULT_METHOD,
        "verify_plan": _default_plan_for_method(DEFAULT_METHOD),
        "evidence_history": [],
        "last_status": None,
        "last_run_at": None,
    }


def normalize_ac_list(items: Any) -> List[Dict[str, Any]]:
    """لیست AC را normalize می‌کند. AC های با text خالی حذف می‌شوند."""
    if not items or not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in items:
        norm = normalize_ac(item)
        if norm.get("text"):
            out.append(norm)
    return out


def normalize_task_step(step: Any) -> Dict[str, Any]:
    """یک task_step را normalize می‌کند تا verify_method + verify_plan داشته باشد.

    فیلدهای موجود حفظ می‌شوند (id/title/scope/status/...). فقط فیلدهای
    runtime-verify اضافه می‌شوند اگر نباشند.
    """
    if not isinstance(step, dict):
        return {
            "id": 1,
            "title": str(step) if step is not None else "",
            "scope": "",
            "status": "pending",
            "completion_pct": 0,
            "verify_method": DEFAULT_METHOD,
            "verify_plan": _default_plan_for_method(DEFAULT_METHOD),
        }
    out = dict(step)
    out.setdefault("status", "pending")
    out.setdefault("completion_pct", 0)
    method = _coerce_method(out.get("verify_method"))
    out["verify_method"] = method
    plan = out.get("verify_plan")
    if not isinstance(plan, dict):
        plan = _default_plan_for_method(method)
    else:
        base = _default_plan_for_method(method)
        base.update(plan)
        plan = base
    out["verify_plan"] = plan
    return out


def normalize_task_steps(steps: Any) -> List[Dict[str, Any]]:
    if not steps or not isinstance(steps, list):
        return []
    return [normalize_task_step(s) for s in steps]
