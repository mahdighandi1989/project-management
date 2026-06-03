"""Tests for the Claude Auto-Runner workflow + dynamic model selection.

Guards the recent fix that:
  - Removed the hard-coded `--model claude-opus-4-8` placeholder.
  - Added a `claude_model` workflow input so backend can pass the latest
    Opus/Sonnet/Haiku per task at dispatch time.
  - Wires `pick_model_for_task` (which delegates to the same picker used
    by Cloud Code inspector chat) into all three dispatch sites.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Workflow YAML — no model hardcoded
# ---------------------------------------------------------------------------


def test_workflow_yaml_does_not_hardcode_a_specific_model_id():
    from app.services.claude_runner_bootstrap import build_workflow_yaml

    yaml = build_workflow_yaml(
        watched_id="w1",
        repo_full_name="owner/repo",
        branch="main",
    )
    # The dead placeholder must be gone.
    assert "claude-opus-4-8" not in yaml
    # No dated model id should be baked in either — the model must come
    # from the workflow input so backend can pick the freshest.
    assert "claude-opus-4-5" not in yaml
    assert "claude-sonnet-4-5" not in yaml
    assert "claude-haiku-4-5" not in yaml


def test_workflow_yaml_declares_claude_model_input():
    from app.services.claude_runner_bootstrap import build_workflow_yaml

    yaml = build_workflow_yaml(
        watched_id="w1",
        repo_full_name="owner/repo",
    )
    assert "claude_model:" in yaml
    assert "target_task_id:" in yaml


def test_workflow_yaml_routes_model_through_input_with_sonnet_fallback():
    from app.services.claude_runner_bootstrap import build_workflow_yaml

    yaml = build_workflow_yaml(
        watched_id="w1",
        repo_full_name="owner/repo",
    )
    # The action must consume the input expression and fall back to
    # `sonnet` (the Claude Code CLI alias for "latest Sonnet") when no
    # input is supplied.
    assert "github.event.inputs.claude_model" in yaml
    assert "'sonnet'" in yaml


# ---------------------------------------------------------------------------
# pick_model_for_task delegates to the cloud_code picker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pick_model_for_task_returns_none_without_oauth(monkeypatch):
    from app.services import claude_runner_bootstrap as crb

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    task = SimpleNamespace(
        id="t1", title="refactor everything", raw_idea="", prompt="long body",
    )
    got = await crb.pick_model_for_task(task)
    assert got is None


@pytest.mark.asyncio
async def test_pick_model_for_task_routes_heavy_task_to_latest_opus(monkeypatch):
    from app.services import claude_runner_bootstrap as crb
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    async def fake_list(force_refresh=False):
        return [
            {"id": "claude-opus-4-5-20251101", "created_at": "2025-11-01"},
            {"id": "claude-opus-5-0-20260301", "created_at": "2026-03-01"},
            {"id": "claude-sonnet-4-5-20250929", "created_at": "2025-09-29"},
        ]

    monkeypatch.setattr(ccs, "list_available_models", fake_list)

    task = SimpleNamespace(
        id="t1",
        title="بازنویسی معماری کل پروژه",
        raw_idea="",
        prompt="refactor every module end-to-end",
    )
    got = await crb.pick_model_for_task(task)
    # newest opus must win
    assert got == "claude-opus-5-0-20260301"


@pytest.mark.asyncio
async def test_pick_model_for_task_routes_simple_to_haiku(monkeypatch):
    from app.services import claude_runner_bootstrap as crb
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    async def fake_list(force_refresh=False):
        return [
            {"id": "claude-haiku-4-5-20251001", "created_at": "2025-10-01"},
            {"id": "claude-sonnet-4-5-20250929", "created_at": "2025-09-29"},
        ]

    monkeypatch.setattr(ccs, "list_available_models", fake_list)

    task = SimpleNamespace(
        id="t1", title="سلام", raw_idea="", prompt="سلام",
    )
    got = await crb.pick_model_for_task(task)
    assert got == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# trigger_workflow_dispatch forwards claude_model as a workflow input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_workflow_dispatch_passes_claude_model_input():
    """The HTTP call to GitHub /dispatches must include claude_model in inputs."""
    from app.services import claude_runner_bootstrap as crb

    watched = SimpleNamespace(
        id="w1",
        repo_full_name="owner/repo",
        github_repo="owner/repo",
        claude_runner_enabled=True,
        claude_runner_workflow_path=".github/workflows/claude-auto-task-runner.yml",
    )

    captured = {}

    class FakePR:
        GITHUB_API = "https://api.github.com"

        def _get_headers(self, token):
            return {"Authorization": f"Bearer {token}"}

        async def _gh_request(self, method, url, headers, json_body):
            captured["url"] = url
            captured["body"] = json_body
            return {"status": 204, "body_text": ""}

    fake_pr = FakePR()

    # get_oversight_service is imported lazily inside the function, so we
    # patch its source module — that's where the bound name resolves.
    fake_ovs = SimpleNamespace(is_watched_verify_locked=lambda _id: False)
    with patch("app.services.claude_runner_bootstrap.get_github_pr_service", return_value=fake_pr), \
         patch(
             "app.services.claude_runner_bootstrap._resolve_repo_and_branch",
             return_value=("owner", "repo", "main"),
         ), \
         patch("app.services.oversight_service.get_oversight_service", return_value=fake_ovs):
        result = await crb.trigger_workflow_dispatch(
            watched,
            gh_token="ghp_x",
            target_task_id="task-123",
            claude_model="claude-opus-5-0-20260301",
        )

    assert result["success"] is True
    assert "inputs" in captured["body"]
    assert captured["body"]["inputs"]["claude_model"] == "claude-opus-5-0-20260301"
    assert captured["body"]["inputs"]["target_task_id"] == "task-123"


@pytest.mark.asyncio
async def test_trigger_workflow_dispatch_omits_claude_model_when_none():
    """When no model is picked (e.g., no OAuth token), input is omitted so
    the YAML's own default (`sonnet`) takes over."""
    from app.services import claude_runner_bootstrap as crb

    watched = SimpleNamespace(
        id="w1",
        repo_full_name="owner/repo",
        github_repo="owner/repo",
        claude_runner_enabled=True,
        claude_runner_workflow_path=".github/workflows/claude-auto-task-runner.yml",
    )

    captured = {}

    class FakePR:
        GITHUB_API = "https://api.github.com"

        def _get_headers(self, token):
            return {"Authorization": f"Bearer {token}"}

        async def _gh_request(self, method, url, headers, json_body):
            captured["body"] = json_body
            return {"status": 204, "body_text": ""}

    fake_pr = FakePR()
    # get_oversight_service is imported lazily inside the function, so we
    # patch its source module — that's where the bound name resolves.
    fake_ovs = SimpleNamespace(is_watched_verify_locked=lambda _id: False)
    with patch("app.services.claude_runner_bootstrap.get_github_pr_service", return_value=fake_pr), \
         patch(
             "app.services.claude_runner_bootstrap._resolve_repo_and_branch",
             return_value=("owner", "repo", "main"),
         ), \
         patch("app.services.oversight_service.get_oversight_service", return_value=fake_ovs):
        await crb.trigger_workflow_dispatch(
            watched,
            gh_token="ghp_x",
            target_task_id=None,
            claude_model=None,
        )

    # Either no `inputs` at all, or `inputs` without claude_model.
    body = captured["body"]
    if "inputs" in body:
        assert "claude_model" not in body["inputs"]


@pytest.mark.asyncio
async def test_trigger_workflow_dispatch_retries_when_yaml_lacks_claude_model_input():
    """If the deployed YAML predates the claude_model input, GitHub returns
    422 'Unexpected inputs'. The dispatcher must auto-retry without the
    claude_model field and surface a clear outdated_workflow warning,
    keeping target_task_id intact."""
    from app.services import claude_runner_bootstrap as crb

    watched = SimpleNamespace(
        id="w1",
        repo_full_name="owner/repo",
        github_repo="owner/repo",
        claude_runner_enabled=True,
        claude_runner_workflow_path=".github/workflows/claude-auto-task-runner.yml",
    )

    call_log = []

    class FakePR:
        GITHUB_API = "https://api.github.com"

        def _get_headers(self, token):
            return {"Authorization": f"Bearer {token}"}

        async def _gh_request(self, method, url, headers, json_body):
            call_log.append(json_body)
            if len(call_log) == 1:
                # first attempt with claude_model → 422
                return {
                    "status": 422,
                    "body_text": '{"message":"Unexpected inputs: claude_model"}',
                }
            # retry without claude_model → 204
            return {"status": 204, "body_text": ""}

    fake_pr = FakePR()
    # get_oversight_service is imported lazily inside the function, so we
    # patch its source module — that's where the bound name resolves.
    fake_ovs = SimpleNamespace(is_watched_verify_locked=lambda _id: False)
    with patch("app.services.claude_runner_bootstrap.get_github_pr_service", return_value=fake_pr), \
         patch(
             "app.services.claude_runner_bootstrap._resolve_repo_and_branch",
             return_value=("owner", "repo", "main"),
         ), \
         patch("app.services.oversight_service.get_oversight_service", return_value=fake_ovs):
        res = await crb.trigger_workflow_dispatch(
            watched,
            gh_token="ghp_x",
            target_task_id="task-123",
            claude_model="claude-opus-5-0",
        )

    assert res["success"] is True
    assert res.get("outdated_workflow") is True
    # first call had claude_model; retry must keep target_task_id but drop claude_model
    assert call_log[0]["inputs"]["claude_model"] == "claude-opus-5-0"
    assert "claude_model" not in call_log[1]["inputs"]
    assert call_log[1]["inputs"]["target_task_id"] == "task-123"
