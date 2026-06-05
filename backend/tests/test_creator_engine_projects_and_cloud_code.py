"""🚨 Two regressions on /creator (Creator Engine) page.

Issue 1: Projects created via Telegram disappear from the panel.
─────────────────────────────────────────────────────────────────
The user reported: "پروژه‌ای که قبلا از طریق تلگرام ساخته بودم بازم رفته"
— "the project I previously created via Telegram is gone again". This
regression has happened before; I claimed I fixed it.

Root cause: `get_simple_creator()` was hardcoded to pass `"./projects"`
to the constructor, completely bypassing the careful persistence
fallback chain in `__init__` (which checks env, then writable disk
paths in priority order, ending in /tmp as last resort). On Render,
`./projects` resolves to `/app/projects` — an EPHEMERAL path that is
wiped on every deploy. The persistent disk is mounted at
`/app/storage` (per render.yaml). So every redeploy → projects gone.

The half-fix that was previously claimed: I added the persistence
fallback chain in `__init__` (lines 80-97), but never updated the
singleton accessor to use it. Classic half-applied refactor.

Fix: `get_simple_creator()` now passes `None` so `__init__` runs the
fallback chain.

Issue 2: cloud_code (Claude OAuth) doesn't appear as an active model
─────────────────────────────────────────────────────────────────
The user has CLAUDE_CODE_OAUTH_TOKEN set and cloud_code shows up on
the Models page. But on /creator the active-models list shows only
DeepSeek + Gemini — cloud_code is missing.

Root cause: `ai_manager.get_available_models()` only returned models
whose provider exists in `self._services` (API-key-based providers:
OpenAI/Claude/Gemini/DeepSeek/Perplexity). cloud_code uses OAuth and
registers via `oauth_model_registry` (a separate path). So it was
filtered out.

Additionally `ai_manager.generate(model_id="cloud_code", ...)` failed
with "Provider not available" — only `oversight_service._ai_generate`
knew how to route OAuth models. Other callers (simple_projects'
`ai_generate`, Creator engine, etc.) silently fell back to DeepSeek.

Fix: ai_manager now consults `oauth_model_registry` in BOTH:
  (a) `get_available_models()` — model included if OAuth dispatcher exists
  (b) `generate()` — request routed via dispatcher if registered

This makes cloud_code first-class through the same ai_manager API,
so every caller (Creator, simple_projects, anything else that uses
ai_manager) gets it automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Issue 1: simple_creator singleton uses persistence fallback
# ---------------------------------------------------------------------------


def test_get_simple_creator_does_not_hardcode_relative_path():
    """🚨 Regression guard: the singleton accessor must NOT pass a
    hardcoded relative path (or any non-None workspace) — that bypasses
    the persistence fallback and Render projects disappear on redeploy."""
    src = (
        Path(__file__).resolve().parents[1] / "app/services/simple_creator.py"
    ).read_text(encoding="utf-8")
    idx = src.find("def get_simple_creator")
    assert idx != -1
    body = src[idx:idx + 1500]
    # Must NOT contain the old hardcoded path
    assert 'SimpleProjectCreator("./projects")' not in body, (
        "get_simple_creator must NOT hardcode './projects' — that maps to "
        "the ephemeral /app/projects on Render. Pass None so __init__'s "
        "persistence fallback (./storage/projects → /app/storage/projects) "
        "is used."
    )
    # Must call SimpleProjectCreator() with no positional workspace arg
    assert "SimpleProjectCreator()" in body, (
        "get_simple_creator must call SimpleProjectCreator() with no args "
        "so the __init__ fallback chain runs and picks the persistent disk"
    )


def test_simple_creator_init_uses_storage_path_in_priority_order():
    """The __init__ fallback must put persistent paths BEFORE ephemeral
    ones. Otherwise on Render we'd still land in /tmp/projects."""
    src = (
        Path(__file__).resolve().parents[1] / "app/services/simple_creator.py"
    ).read_text(encoding="utf-8")
    idx = src.find("def __init__")
    body = src[idx:idx + 2000]
    # storage/projects must come before projects (relative ephemeral) and /tmp
    storage_idx = body.find("storage/projects")
    tmp_idx = body.find("/tmp/projects")
    assert storage_idx != -1, "persistent storage candidate must be present"
    assert tmp_idx != -1, "ephemeral /tmp candidate must be present as last resort"
    assert storage_idx < tmp_idx, (
        "persistent /app/storage/projects must be tried BEFORE /tmp/projects "
        "— otherwise on Render with the disk mounted we'd still default to "
        "ephemeral storage"
    )


# ---------------------------------------------------------------------------
# Issue 2: cloud_code appears in get_available_models when dispatcher exists
# ---------------------------------------------------------------------------


def test_get_available_models_includes_cloud_code_when_dispatcher_registered():
    """When cloud_code's OAuth dispatcher is registered (which happens at
    app startup via main.py's eager import), get_available_models MUST
    include it — so the Creator page's pill list, the Inspector chat's
    model picker, and any other ai_manager consumer sees cloud_code."""
    from app.services.ai_manager import get_ai_manager
    from app.services import oauth_model_registry as omr

    # Ensure cloud_code is registered (test env may need explicit import)
    omr._BOOTSTRAP_DONE = False
    # Trigger bootstrap by querying
    omr.is_oauth_model("cloud_code")

    # Mock the env so cloud_code_is_configured returns True
    with patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "test-token"}):
        mgr = get_ai_manager()
        models = mgr.get_available_models()

    ids = [m.id for m in models]
    assert "cloud_code" in ids, (
        f"cloud_code must appear in available models when its OAuth "
        f"dispatcher is registered. Got: {ids}"
    )


def test_get_available_models_excludes_cloud_code_when_disabled_in_db():
    """If the user has disabled cloud_code in the Models page settings,
    it must be excluded — same as any other model with enabled=False."""
    from app.services.ai_manager import get_ai_manager
    from app.services import oauth_model_registry as omr
    from app.core.database import SessionLocal
    from app.models.ai_profile import ModelSettings

    omr._BOOTSTRAP_DONE = False
    omr.is_oauth_model("cloud_code")

    # Set cloud_code disabled in DB
    db = SessionLocal()
    try:
        existing = db.query(ModelSettings).filter(
            ModelSettings.model_id == "cloud_code",
        ).first()
        if existing:
            existing.enabled = False
        else:
            db.add(ModelSettings(model_id="cloud_code", enabled=False))
        db.commit()

        with patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "test-token"}):
            mgr = get_ai_manager()
            models = mgr.get_available_models()

        ids = [m.id for m in models]
        assert "cloud_code" not in ids, (
            "cloud_code must respect the same DB enabled=False switch as "
            "any other model"
        )
    finally:
        # Clean up: re-enable so other tests aren't affected
        try:
            existing = db.query(ModelSettings).filter(
                ModelSettings.model_id == "cloud_code",
            ).first()
            if existing:
                existing.enabled = True
                db.commit()
        except Exception:
            pass
        db.close()


# ---------------------------------------------------------------------------
# Issue 2b: ai_manager.generate routes cloud_code via OAuth dispatcher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_manager_generate_routes_cloud_code_through_oauth_dispatcher():
    """🚨 The actual bug that hid cloud_code from every ai_manager caller:
    ai_manager.generate(model_id='cloud_code', ...) used to fail with
    'Provider not available' because cloud_code isn't in self._services.

    The fix: consult oauth_model_registry first. If a dispatcher exists,
    route through it and wrap the string response into AIResponse.

    This makes simple_projects' ai_generate (and every other caller) work
    for cloud_code without per-caller special-casing."""
    from app.services.ai_manager import get_ai_manager
    from app.services.ai_base import Message
    from app.services import oauth_model_registry as omr

    # Register a fake dispatcher to avoid hitting Anthropic API
    captured = {}

    async def fake_dispatcher(prompt, *, max_tokens=1024, temperature=0.7):
        captured["prompt"] = prompt
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        return "FAKE_OAUTH_RESPONSE"

    omr.register_oauth_dispatcher("test_oauth_model", fake_dispatcher)
    try:
        mgr = get_ai_manager()
        response = await mgr.generate(
            model_id="test_oauth_model",
            messages=[Message(role="user", content="hello world")],
            max_tokens=2000,
            temperature=0.5,
        )
        assert response.content == "FAKE_OAUTH_RESPONSE"
        assert response.model_id == "test_oauth_model"
        assert "hello world" in captured["prompt"]
        assert captured["max_tokens"] == 2000
        assert captured["temperature"] == 0.5
    finally:
        omr._REGISTRY.pop("test_oauth_model", None)


def test_get_available_models_hides_cloud_code_when_token_missing():
    """Parity with API-key providers: if DEEPSEEK_API_KEY is missing,
    DeepSeek models don't appear. Same for cloud_code without
    CLAUDE_CODE_OAUTH_TOKEN — otherwise user sees a pill, clicks it,
    and gets a runtime error 'CLAUDE_CODE_OAUTH_TOKEN ست نشده' which
    is bad UX. Hide it from the list when not configured."""
    from app.services.ai_manager import get_ai_manager
    from app.services import oauth_model_registry as omr

    omr._BOOTSTRAP_DONE = False
    omr.is_oauth_model("cloud_code")

    # Explicitly clear the token
    import os as _os
    saved = _os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    try:
        mgr = get_ai_manager()
        models = mgr.get_available_models()
        ids = [m.id for m in models]
        assert "cloud_code" not in ids, (
            "cloud_code must be hidden when CLAUDE_CODE_OAUTH_TOKEN is missing "
            "— parity with API-key providers that hide when key is missing"
        )
    finally:
        if saved is not None:
            _os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = saved


@pytest.mark.asyncio
async def test_ai_manager_generate_combines_multi_turn_messages_for_oauth():
    """The OAuth dispatcher takes a single prompt string but ai_manager's
    contract is a list of messages. The combination must preserve all
    turns so multi-turn conversations work for cloud_code too."""
    from app.services.ai_manager import get_ai_manager
    from app.services.ai_base import Message
    from app.services import oauth_model_registry as omr

    captured = {}

    async def fake_dispatcher(prompt, **kw):
        captured["prompt"] = prompt
        return "ok"

    omr.register_oauth_dispatcher("test_multi", fake_dispatcher)
    try:
        mgr = get_ai_manager()
        await mgr.generate(
            model_id="test_multi",
            messages=[
                Message(role="system", content="You are helpful."),
                Message(role="user", content="What's 2+2?"),
                Message(role="assistant", content="4"),
                Message(role="user", content="And 3+3?"),
            ],
            max_tokens=100,
        )
        prompt = captured["prompt"]
        # All four messages must appear in the combined prompt
        assert "You are helpful" in prompt
        assert "What's 2+2?" in prompt
        assert "4" in prompt
        assert "And 3+3?" in prompt
    finally:
        omr._REGISTRY.pop("test_multi", None)
