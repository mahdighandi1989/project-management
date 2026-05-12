"""Stage 1 — AC normalization & backward-compat tests.

این تست‌ها مطمئن می‌شوند که:
1. AC string قدیمی → بعد از normalize ساختار {text, verify_method=static, ...} می‌گیرد
2. AC dict جدید → دست‌نخورده باقی می‌ماند (فقط فیلدهای کم پر می‌شوند)
3. task_steps هم همان رفتار را دارند
4. method نامعتبر → fallback به static
5. mixed list (ترکیب str + dict) → همه نرمال می‌شوند
"""

import pytest
from app.services.verify_runtime import (
    normalize_ac,
    normalize_ac_list,
    normalize_task_step,
    normalize_task_steps,
    AC_METHODS,
    DEFAULT_METHOD,
)


class TestNormalizeAc:
    def test_legacy_string_ac(self):
        r = normalize_ac("وقتی X کلیک شد، Y باز شود")
        assert r["text"] == "وقتی X کلیک شد، Y باز شود"
        assert r["verify_method"] == "static"
        assert isinstance(r["verify_plan"], dict)
        assert "grep_patterns" in r["verify_plan"]
        assert r["evidence_history"] == []
        assert r["last_status"] is None
        assert r["last_run_at"] is None

    def test_new_dict_ac_with_full_plan(self):
        ac = {
            "text": "GET /api/x → 200",
            "verify_method": "api_response",
            "verify_plan": {
                "method": "GET",
                "path": "/api/x",
                "expected_status": 200,
                "required_fields": ["id", "name"],
            },
        }
        r = normalize_ac(ac)
        assert r["verify_method"] == "api_response"
        assert r["verify_plan"]["path"] == "/api/x"
        assert r["verify_plan"]["required_fields"] == ["id", "name"]
        assert r["verify_plan"]["expected_status"] == 200

    def test_invalid_method_falls_back_to_static(self):
        ac = {"text": "X", "verify_method": "totally_made_up"}
        r = normalize_ac(ac)
        assert r["verify_method"] == "static"

    def test_dict_without_plan_gets_default_plan(self):
        ac = {"text": "X", "verify_method": "ui_interaction"}
        r = normalize_ac(ac)
        assert "ui_steps" in r["verify_plan"]
        assert r["verify_plan"]["ui_steps"] == []
        assert r["verify_plan"]["base"] == "frontend"

    def test_none_input(self):
        r = normalize_ac(None)
        assert r["text"] == ""
        assert r["verify_method"] == "static"

    def test_int_input_coerced_to_str(self):
        r = normalize_ac(42)
        assert r["text"] == "42"

    def test_empty_string_ac_stays_empty(self):
        r = normalize_ac("")
        assert r["text"] == ""
        assert r["verify_method"] == "static"


class TestNormalizeAcList:
    def test_mixed_legacy_and_new(self):
        mixed = [
            "legacy A",
            {"text": "new B", "verify_method": "ui_interaction"},
            "legacy C",
        ]
        r = normalize_ac_list(mixed)
        assert len(r) == 3
        assert r[0]["verify_method"] == "static"
        assert r[1]["verify_method"] == "ui_interaction"
        assert r[2]["verify_method"] == "static"

    def test_empty_items_filtered(self):
        mixed = ["a", None, "", {"text": ""}, "b"]
        r = normalize_ac_list(mixed)
        assert len(r) == 2
        assert [x["text"] for x in r] == ["a", "b"]

    def test_none_input_returns_empty(self):
        assert normalize_ac_list(None) == []
        assert normalize_ac_list([]) == []

    def test_evidence_history_capped(self):
        ac = {
            "text": "X",
            "verify_method": "static",
            "evidence_history": [{"run_id": str(i)} for i in range(50)],
        }
        r = normalize_ac(ac)
        assert len(r["evidence_history"]) == 20


class TestNormalizeTaskStep:
    def test_step_without_verify_method(self):
        step = {"id": 1, "title": "A", "scope": "X", "status": "pending"}
        r = normalize_task_step(step)
        assert r["verify_method"] == "static"
        assert "verify_plan" in r
        # original fields preserved
        assert r["id"] == 1
        assert r["title"] == "A"
        assert r["scope"] == "X"

    def test_step_with_verify_method_preserved(self):
        step = {
            "id": 2,
            "title": "ui step",
            "verify_method": "ui_interaction",
            "verify_plan": {"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}]},
        }
        r = normalize_task_step(step)
        assert r["verify_method"] == "ui_interaction"
        assert r["verify_plan"]["ui_steps"][0]["action"] == "navigate"

    def test_invalid_step_input(self):
        r = normalize_task_step("just a string step")
        assert r["title"] == "just a string step"
        assert r["verify_method"] == "static"

    def test_normalize_task_steps_list(self):
        steps = [
            {"id": 1, "title": "A"},
            {"id": 2, "title": "B", "verify_method": "api_response"},
        ]
        r = normalize_task_steps(steps)
        assert len(r) == 2
        assert r[0]["verify_method"] == "static"
        assert r[1]["verify_method"] == "api_response"


class TestBackwardCompat:
    """تست critical: همه AC method ها در constants هستند."""

    def test_all_methods_in_constants(self):
        for m in ("static", "ui_interaction", "api_response", "backend_test", "manual_only"):
            assert m in AC_METHODS

    def test_default_method_is_static(self):
        assert DEFAULT_METHOD == "static"
