"""Post-stage4 UX/capability fixes.

After the user opened the models page and clicked into the edit modal
for the cloud_code row, two issues surfaced:

1. The edit modal showed ALL task types (همه‌کارها / چت / تحلیل سلامت
   / تولید کد / …) for the cloud_code row. Those legacy keys are NOT
   consulted by the central helper — only the 4 cloud_code-specific
   keys (claude_auto_runner, claude_single_task, inspector_cloud_code,
   creator_engine) actually drive routing. Checking the legacy keys did
   nothing, which is misleading UX. Conversely, the 4 new keys appeared
   on every other model's row even though they're meaningless there.

   Fix (frontend): introduce CLOUD_CODE_TASK_KEYS in models/page.tsx
   and filter both allowed_tasks and preferred_for columns so:
     - cloud_code row shows only the 4 keys (+'all' in allowed_tasks)
     - every other row hides the 4 cloud_code-specific keys

2. Capability test for cloud_code reported 0/0/0 across the board.
   Cause: model_capability_tester._run_single_test calls
   ai_manager.generate(model_id="cloud_code"), but cloud_code isn't
   registered in ai_manager._services (it uses OAuth, not an API key).
   The generate call fails silently, every category scores 0.

   Fix (backend): in _run_single_test, when model_id == "cloud_code",
   route directly to cloud_code_complete() with the auto tier picker.
   Other models keep their legacy ai_manager path unchanged.

This file pins both fixes at the source level so a future refactor
can't quietly drop them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Capability test routes cloud_code through cloud_code_complete
# ---------------------------------------------------------------------------


def test_capability_tester_special_cases_cloud_code():
    """Source check — the test runner must detect model_id == 'cloud_code'
    and route through cloud_code_complete instead of ai_manager.generate.
    Otherwise the cloud_code row will keep showing 0 scores."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/model_capability_tester.py"
    )
    src = src_path.read_text(encoding="utf-8")
    idx = src.find("async def _run_single_test")
    assert idx != -1, "_run_single_test method not found"
    # Slice to the next def.
    rest = src[idx + 1:]
    nxt = rest.find("\n    async def ")
    if nxt == -1:
        nxt = rest.find("\n    def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert 'model_id == "cloud_code"' in body, (
        "_run_single_test must short-circuit cloud_code to cloud_code_complete"
    )
    assert "cloud_code_complete" in body, (
        "must call cloud_code_complete on the cloud_code branch"
    )
    # The legacy ai_manager path must remain for other models.
    assert "self.ai_manager.generate" in body, (
        "legacy ai_manager path must remain for non-cloud_code models"
    )


def test_capability_tester_raises_clear_error_without_token():
    """If user clicks 'test capability' on cloud_code without setting the
    env token, they should get a clear Persian message — not a silent 0."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/model_capability_tester.py"
    )
    src = src_path.read_text(encoding="utf-8")
    assert "CLAUDE_CODE_OAUTH_TOKEN" in src, (
        "error message must mention the actual env var name"
    )


def test_capability_tester_uses_min_tier_sonnet_for_cloud_code():
    """🚨 (capability test fairness fix v2) — قبلاً tier_hint="opus" ست
    شده بود، که برای subscription های Pro tier (با Opus quota محدود)
    429/403 می‌گرفت → همهٔ تست‌ها fail → 0/0/0. کاربر این را گزارش کرد.

    حل صحیح: min_tier="sonnet" (در همهٔ tier های subscription موجود).
    اجازه می‌دهد classifier برای prompts با keyword سنگین Opus بزند،
    ولی برای prompts ساده به Sonnet floor می‌شود (نه Haiku). نتیجه:
    امتیاز منصفانه (70-90 برای Sonnet 4.6) سازگار با همهٔ tier ها."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/model_capability_tester.py"
    )
    src = src_path.read_text(encoding="utf-8")
    idx = src.find("if model_id == \"cloud_code\":")
    assert idx != -1
    body = src[idx:idx + 3000]
    # The new approach uses min_tier="sonnet"
    assert 'min_tier="sonnet"' in body, (
        "capability tester must pass min_tier='sonnet' for cloud_code so "
        "short prompts don't route to Haiku (gives 32/100) while staying "
        "compatible with Pro-tier subscriptions that have limited Opus quota"
    )
    # model="auto" as executable call must NOT appear (it can be in
    # comments documenting prior bug). Check non-comment lines.
    code_lines = [
        ln for ln in body.splitlines()
        if 'model="auto"' in ln and not ln.lstrip().startswith("#")
    ]
    assert code_lines == [], (
        f"model='auto' must not appear as an executable call. "
        f"Found: {code_lines}"
    )


def test_capability_tester_has_haiku_fallback_for_subscription_caps():
    """🛡 Defense in depth: if the min_tier="sonnet" call fails (rate
    limit, subscription cap), the tester must NOT return 0 silently —
    it should retry with tier_hint="haiku" as last resort and propagate
    the original error only if Haiku also fails. This gives the user
    a meaningful score even on the most constrained subscription."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/model_capability_tester.py"
    )
    src = src_path.read_text(encoding="utf-8")
    idx = src.find("if model_id == \"cloud_code\":")
    body = src[idx:idx + 3500]
    assert 'tier_hint="haiku"' in body, (
        "fallback to Haiku must exist for when Sonnet/Opus calls fail "
        "(e.g. subscription cap reached)"
    )


def test_cloud_code_complete_signature_accepts_tier_hint():
    """The cloud_code_complete helper must expose tier_hint so callers
    (like the capability tester) can force a specific tier."""
    from app.services.cloud_code_service import cloud_code_complete
    import inspect

    sig = inspect.signature(cloud_code_complete)
    assert "tier_hint" in sig.parameters, (
        "cloud_code_complete must accept tier_hint so callers can force "
        "a specific tier — used by capability test to force Opus"
    )
    # Backward-compat: default is None (legacy: model arg handles it)
    assert sig.parameters["tier_hint"].default is None


# ---------------------------------------------------------------------------
# Frontend filters the task list correctly
# ---------------------------------------------------------------------------


def test_frontend_defines_cloud_code_task_keys_set():
    """Source check — the frontend must have a constant set of the 4
    cloud_code-specific keys so it can filter both columns consistently."""
    src_path = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/models/page.tsx"
    )
    src = src_path.read_text(encoding="utf-8")
    assert "CLOUD_CODE_TASK_KEYS" in src, (
        "frontend must define CLOUD_CODE_TASK_KEYS for the filter logic"
    )
    # All 4 keys present in that constant.
    for key in (
        "claude_auto_runner",
        "claude_single_task",
        "inspector_cloud_code",
        "creator_engine",
    ):
        assert key in src, f"key {key!r} missing from frontend"


def test_frontend_filters_preferred_for_by_row_kind():
    """The preferred_for checkbox list must filter:
    - cloud_code row → only the 4 cloud_code keys
    - other rows → hide the 4 cloud_code keys

    Look for the isCloudCodeRow ? isCcKey : !isCcKey pattern in the file."""
    src_path = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/models/page.tsx"
    )
    src = src_path.read_text(encoding="utf-8")
    assert "isCloudCodeRow ? isCcKey" in src, (
        "preferred_for filter pattern must depend on isCloudCodeRow"
    )


def test_frontend_filters_allowed_tasks_by_row_kind():
    """Same filter pattern must apply to the allowed_tasks column too,
    otherwise the user can still tick legacy keys for cloud_code."""
    src_path = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/models/page.tsx"
    )
    src = src_path.read_text(encoding="utf-8")
    # 'all' is kept for non-cloud_code rows. The pattern includes 'all' for
    # cloud_code so the user can still pick "همه کارها" if desired.
    assert "isCloudCodeRow ? (isCcKey || task.id === 'all')" in src, (
        "allowed_tasks filter must preserve 'all' option for cloud_code"
    )
