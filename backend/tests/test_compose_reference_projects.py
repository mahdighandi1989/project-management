"""🚨 Regression: compose pipeline (voice/file/multimedia tasks created via
Telegram) must pass selected_projects through to idea_to_prompt and create_task.

Context — what was broken:
==========================

The user created a task via Telegram by sending a voice file. They picked
trading-system as the target project and wanted project-management as a
reference (so the AI would know how Cloud Code / OAuth token integration
was implemented there and adapt it for trading-system).

After looking at the generated PDF, NO reference project was used:
  - The "## 📚 پروژه‌های مرجع" block was missing from the prompt
  - Zero mention of project-management files (cloud_code_service.py, etc.)
  - The AI invented a generic "CloudToken" abstraction instead of describing
    the actual Claude Code OAuth pattern (CLI impersonation, Bearer auth)
  - No "adapt to current stack" warning that the reference_block normally
    enforces

Root cause discovered:
  1. The Telegram compose flow (voice / file / multimedia path) had NO
     ref-picker step at all. After picking the target project, it went
     straight to submission.
  2. ComposeBuffer had no selected_refs field — even if a picker existed,
     there was nowhere to store the choices.
  3. _compose_run_pipeline_task_inner called idea_to_prompt without the
     selected_projects argument and create_task without selected_projects
     in the payload.

The fix wires all three layers (buffer → picker → pipeline). This file
locks those wirings down. If any of them regresses, the reference-projects
feature silently dies again for the most common Telegram flow.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Layer 1: ComposeBuffer carries selected_refs + refs_asked
# ---------------------------------------------------------------------------


def test_compose_buffer_has_selected_refs_field():
    """The buffer must have somewhere to store the user's ref picks."""
    from app.services.oversight_telegram_compose import ComposeBuffer

    buf = ComposeBuffer(chat_id="123")
    assert hasattr(buf, "selected_refs")
    assert buf.selected_refs == []
    # refs_asked distinguishes "user hasn't been shown the picker yet"
    # from "user saw the picker and chose nothing" — both produce
    # selected_refs=[] but only the latter should skip the picker.
    assert hasattr(buf, "refs_asked")
    assert buf.refs_asked is False


@pytest.mark.asyncio
async def test_compose_set_selected_refs_marks_asked(tmp_path, monkeypatch):
    from app.services import oversight_telegram_compose as otc

    monkeypatch.setattr(otc, "COMPOSE_FILE", tmp_path / "compose.json")
    svc = otc.ComposeService()
    await svc.start("chat-1", mode="task")
    buf = await svc.set_selected_refs("chat-1", ["proj-a", "proj-b"])
    assert buf is not None
    assert buf.selected_refs == ["proj-a", "proj-b"]
    assert buf.refs_asked is True


@pytest.mark.asyncio
async def test_compose_toggle_ref_adds_and_removes(tmp_path, monkeypatch):
    from app.services import oversight_telegram_compose as otc

    monkeypatch.setattr(otc, "COMPOSE_FILE", tmp_path / "compose.json")
    svc = otc.ComposeService()
    await svc.start("chat-1", mode="task")
    # add
    buf = await svc.toggle_selected_ref("chat-1", "proj-a")
    assert buf is not None and buf.selected_refs == ["proj-a"]
    # add another
    buf = await svc.toggle_selected_ref("chat-1", "proj-b")
    assert buf.selected_refs == ["proj-a", "proj-b"]
    # remove first
    buf = await svc.toggle_selected_ref("chat-1", "proj-a")
    assert buf.selected_refs == ["proj-b"]


@pytest.mark.asyncio
async def test_compose_toggle_ref_refuses_self_reference(tmp_path, monkeypatch):
    """A project can't be its own reference. The toggle must drop the
    target watched_id silently — same rule as the text-only flow."""
    from app.services import oversight_telegram_compose as otc

    monkeypatch.setattr(otc, "COMPOSE_FILE", tmp_path / "compose.json")
    svc = otc.ComposeService()
    await svc.start("chat-1", mode="task", watched_id="proj-main")
    buf = await svc.toggle_selected_ref("chat-1", "proj-main")
    assert buf is not None
    assert buf.selected_refs == []


# ---------------------------------------------------------------------------
# Layer 2: pipeline call signatures (static source check — no asyncio needed)
# ---------------------------------------------------------------------------


def _read_pipeline_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/notification_service.py"
    )
    return src_path.read_text(encoding="utf-8")


def test_compose_pipeline_passes_selected_projects_to_idea_to_prompt():
    """🚨 The exact regression. Before the fix, idea_to_prompt was called
    without selected_projects, so the reference_block was never injected
    into the final prompt for voice/file tasks.

    This grep looks for the pipeline's idea_to_prompt call and asserts
    the keyword appears in the SAME call site (not anywhere in the
    file). If a future refactor splits the call, update the markers
    accordingly.
    """
    src = _read_pipeline_source()
    # Find _compose_run_pipeline_task_inner body — the only place that
    # builds the prompt for a compose-mode task.
    marker = "_compose_run_pipeline_task_inner"
    idx = src.find(f"async def {marker}")
    assert idx != -1, f"{marker} not found — test markers stale"
    # Slice from the function definition to the next top-level method.
    # Look for the *next* `    async def ` or `    def ` AFTER idx+1.
    rest = src[idx + 1:]
    next_method = rest.find("\n    async def ")
    if next_method == -1:
        next_method = rest.find("\n    def ")
    body = rest if next_method == -1 else rest[:next_method]
    assert "idea_to_prompt(" in body, "pipeline must call idea_to_prompt"
    # The fix: selected_projects= must appear in the body, in the same
    # call as idea_to_prompt. We check by ensuring it appears in the
    # immediate window around the idea_to_prompt call.
    itp_idx = body.find("idea_to_prompt(")
    assert itp_idx != -1
    window = body[itp_idx:itp_idx + 1500]
    assert "selected_projects=" in window, (
        "compose pipeline must pass selected_projects to idea_to_prompt — "
        "otherwise reference projects are silently dropped for voice/file tasks"
    )


def test_compose_pipeline_passes_selected_projects_to_create_task():
    """Same idea, second hop: create_task receives selected_projects so
    that follow-up flows (regenerate, dup-rebuild) preserve the refs."""
    src = _read_pipeline_source()
    marker = "_compose_run_pipeline_task_inner"
    idx = src.find(f"async def {marker}")
    assert idx != -1
    rest = src[idx + 1:]
    next_method = rest.find("\n    async def ")
    if next_method == -1:
        next_method = rest.find("\n    def ")
    body = rest if next_method == -1 else rest[:next_method]
    # The task payload dict must include selected_projects.
    assert '"selected_projects"' in body, (
        "compose pipeline must include selected_projects in the create_task "
        "payload so regenerate/dup paths keep the user's reference choice"
    )


def test_compose_submit_invokes_ref_picker_before_pipeline():
    """If refs_asked is False, _compose_submit must hand off to
    _compose_pick_refs (not jump straight to the pipeline). This is the
    gate that ensures the user actually sees the picker."""
    src = _read_pipeline_source()
    # _compose_submit body must reference _compose_pick_refs and refs_asked.
    idx = src.find("async def _compose_submit(")
    assert idx != -1
    rest = src[idx + 1:]
    next_method = rest.find("\n    async def ")
    body = rest if next_method == -1 else rest[:next_method]
    assert "_compose_pick_refs" in body, (
        "_compose_submit must call _compose_pick_refs before the pipeline"
    )
    assert "refs_asked" in body, (
        "_compose_submit must gate on buf.refs_asked"
    )


def test_compose_refpick_callback_handler_exists():
    """The callback router must handle compose_refpick:tog / done / skip."""
    src = _read_pipeline_source()
    assert 'data.startswith("compose_refpick:")' in src, (
        "callback handler for compose_refpick: must exist"
    )
    # All three sub-actions must be handled.
    assert "compose_refpick:tog" in src or '"tog"' in src
    # done / skip:
    assert '("done", "skip")' in src or '"done"' in src
