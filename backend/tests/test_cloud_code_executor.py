"""Tests for cloud_code_executor — the Phase 3 tool dispatcher that
turns model tool_use blocks into real GitHub/Render API calls."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from app.services.cloud_code_executor import (  # noqa: E402
    SUPPORTED_TOOLS_PHASE_3,
    build_inspector_executor,
    get_phase_3_tool_schemas,
)


# ---------------------------------------------------------------------------
# Schema surface
# ---------------------------------------------------------------------------


def test_phase_3_tool_schemas_pulled_from_inspector_agent():
    """No second source of truth — schemas come from inspector_agent and
    are filtered to the supported set so the model only sees tools we can
    execute."""
    schemas = get_phase_3_tool_schemas()
    names = {t["name"] for t in schemas}
    assert names <= SUPPORTED_TOOLS_PHASE_3
    # critical tools must be present
    assert "read_file" in names
    assert "list_files" in names
    assert "render_get_env_vars" in names
    assert "render_set_env_var" in names
    assert "submit_action_plan" in names
    # every schema must have the Anthropic shape
    for t in schemas:
        assert "name" in t and "description" in t and "input_schema" in t


def test_supported_tools_match_actual_dispatcher_branches():
    """The SUPPORTED_TOOLS_PHASE_3 set must contain ONLY tools the
    executor actually dispatches. Any orphan there would make the model
    invoke something we silently can't run, wasting iterations."""
    import inspect

    from app.services import cloud_code_executor as ccx

    # Pull the source of build_inspector_executor so we can see which
    # `if name == "..."` branches exist in the dispatcher.
    src = inspect.getsource(ccx.build_inspector_executor)
    dispatched = set()
    import re as _re
    for m in _re.finditer(r'name == "([^"]+)"', src):
        dispatched.add(m.group(1))

    # Every supported tool must have a real dispatcher branch.
    for tool in SUPPORTED_TOOLS_PHASE_3:
        assert tool in dispatched, f"{tool} listed as supported but no dispatcher branch"
    # And no orphan: every branch we wrote should be in the supported set.
    for tool in dispatched:
        assert tool in SUPPORTED_TOOLS_PHASE_3, f"{tool} dispatched but not in SUPPORTED_TOOLS_PHASE_3"


# ---------------------------------------------------------------------------
# File-level tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_file_returns_file_content_with_line_count():
    gh = MagicMock()
    gh.get_file_content = AsyncMock(return_value={
        "success": True,
        "content": "line1\nline2\nline3",
    })
    execute = build_inspector_executor(
        github_svc=gh,
        render_service=None,
        owner="o",
        repo="r",
        branch="main",
        github_token="t",
        file_list=["src/app.py", "README.md"],
    )

    res = await execute("read_file", {"path": "src/app.py"})
    assert res["is_error"] is False
    assert "src/app.py" in res["content"]
    assert "(3 خط)" in res["content"]
    gh.get_file_content.assert_awaited_once_with("o", "r", "src/app.py", branch="main", token="t")


@pytest.mark.asyncio
async def test_read_file_suggests_near_matches_on_miss():
    gh = MagicMock()
    execute = build_inspector_executor(
        github_svc=gh,
        render_service=None,
        owner="o",
        repo="r",
        branch="main",
        github_token=None,
        file_list=["backend/app/main.py", "frontend/src/main.tsx"],
    )
    res = await execute("read_file", {"path": "main.py"})
    assert res["is_error"] is True
    assert "main.py" in res["content"]
    assert "backend/app/main.py" in res["content"]  # suggestion
    # Should not have called GitHub at all
    gh.get_file_content.assert_not_called() if hasattr(gh.get_file_content, "assert_not_called") else None


@pytest.mark.asyncio
async def test_read_file_caches_so_repeated_calls_dont_hit_github():
    gh = MagicMock()
    gh.get_file_content = AsyncMock(return_value={"success": True, "content": "hi"})
    execute = build_inspector_executor(
        github_svc=gh,
        render_service=None,
        owner="o",
        repo="r",
        branch="main",
        github_token="t",
        file_list=["a.py"],
    )
    await execute("read_file", {"path": "a.py"})
    await execute("read_file", {"path": "a.py"})
    assert gh.get_file_content.await_count == 1


@pytest.mark.asyncio
async def test_list_files_filter_returns_matching_paths():
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=None,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=["src/a.py", "src/b.py", "docs/README.md"],
    )
    res = await execute("list_files", {"filter": "src/"})
    assert res["is_error"] is False
    assert "src/a.py" in res["content"]
    assert "src/b.py" in res["content"]
    assert "docs/README.md" not in res["content"]


# ---------------------------------------------------------------------------
# Render tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_tools_decline_gracefully_when_no_render_service():
    """If the user has no Render token configured, render_service is None
    and every Render tool returns a polite is_error rather than crashing —
    so the model can keep working on file/git tasks."""
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=None,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=[],
    )
    res = await execute("render_get_env_vars", {"service_id": "svc"})
    assert res["is_error"] is True
    assert "Render" in res["content"]


@pytest.mark.asyncio
async def test_render_set_env_var_calls_through_to_render_service():
    """The user's stated use case: Cloud Code sets a Render env var."""
    rsvc = MagicMock()
    rsvc.set_env_var = AsyncMock(return_value={"success": True})
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=rsvc,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=[],
    )
    res = await execute("render_set_env_var", {
        "service_id": "srv-abc",
        "key": "VITE_API_KEY",
        "value": "AIza...",
    })
    assert res["is_error"] is False
    assert "VITE_API_KEY" in res["content"]
    rsvc.set_env_var.assert_awaited_once_with("srv-abc", "VITE_API_KEY", "AIza...")


@pytest.mark.asyncio
async def test_render_set_env_var_surfaces_render_failure():
    rsvc = MagicMock()
    rsvc.set_env_var = AsyncMock(return_value={"success": False, "error": "401 unauthorized"})
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=rsvc,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=[],
    )
    res = await execute("render_set_env_var", {
        "service_id": "x", "key": "K", "value": "v",
    })
    assert res["is_error"] is True
    assert "401" in res["content"]


@pytest.mark.asyncio
async def test_render_trigger_deploy_passes_clear_cache_flag():
    rsvc = MagicMock()
    rsvc.trigger_deploy = AsyncMock(return_value={"success": True})
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=rsvc,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=[],
    )
    await execute("render_trigger_deploy", {"service_id": "x", "clear_cache": True})
    rsvc.trigger_deploy.assert_awaited_once_with("x", clear_cache=True)


# ---------------------------------------------------------------------------
# submit_action_plan + unsupported
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_action_plan_fires_callback_and_acknowledges():
    captured: List[Dict[str, Any]] = []
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=None,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=[],
        on_submit_action_plan=lambda plan: captured.append(plan),
    )
    plan = {"summary": "x", "files": [{"path": "a.py", "operation": "modify"}]}
    res = await execute("submit_action_plan", plan)
    assert res["is_error"] is False
    assert len(captured) == 1
    assert captured[0]["summary"] == "x"


@pytest.mark.asyncio
async def test_unsupported_tool_returns_friendly_decline():
    """An unknown / not-yet-wired tool name yields a recoverable error so
    the agent can apologise rather than the loop crashing."""
    execute = build_inspector_executor(
        github_svc=MagicMock(),
        render_service=None,
        owner="o", repo="r", branch="main", github_token=None,
        file_list=[],
    )
    # render_create_postgres is now wired (see SUPPORTED_TOOLS_PHASE_3).
    # Use a tool name that genuinely doesn't have a handler.
    res = await execute("totally_unknown_tool_xyz", {})
    assert res["is_error"] is True
    assert "Local AI" in res["content"]


def test_create_service_tools_are_in_supported_phase_3_allowlist():
    """🐛 (user-reported) Inspector chat said it had only 10 tools and
    couldn't create services. Root cause: the SUPPORTED_TOOLS_PHASE_3
    allowlist filtered out render_create_service / render_create_redis /
    render_create_postgres even though _build_tools() declared them.

    Pin all three in the allowlist so a future refactor can't silently
    drop them again."""
    from app.services.cloud_code_executor import SUPPORTED_TOOLS_PHASE_3

    for tool_name in (
        "render_create_service",
        "render_create_redis",
        "render_create_postgres",
    ):
        assert tool_name in SUPPORTED_TOOLS_PHASE_3, (
            f"{tool_name} must be in SUPPORTED_TOOLS_PHASE_3 — without it "
            f"the Cloud Code agent reports «I can only manage existing "
            f"services» and the user has to click in the dashboard"
        )


@pytest.mark.asyncio
async def test_executor_catches_unexpected_exceptions():
    """Any unhandled exception in the backend service must be turned into
    a normal is_error tool_result — the loop never crashes."""
    gh = MagicMock()
    gh.get_file_content = AsyncMock(side_effect=RuntimeError("boom"))
    execute = build_inspector_executor(
        github_svc=gh,
        render_service=None,
        owner="o", repo="r", branch="main", github_token="t",
        file_list=["a.py"],
    )
    res = await execute("read_file", {"path": "a.py"})
    assert res["is_error"] is True
    assert "boom" in res["content"]
