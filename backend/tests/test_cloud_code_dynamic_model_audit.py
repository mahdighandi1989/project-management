"""Dynamic model selection audit + min_tier floor.

User showed a screenshot where Cloud Code in inspector chat said
"I am Claude 3.5 Sonnet" while the dropdown listed Claude Sonnet 4.6
as the current Sonnet. They asked: did I hardcode a specific model?
And why is a weak model answering an introduction question?

Investigation results:

1. **Nothing in the production happy path is hardcoded.**
   `pick_best_model` calls `list_available_models()` which hits
   `/v1/models` (1-hour cache) and picks the newest revision in
   the chosen tier. Every consumer (auto-runner, single-task,
   inspector chat, capability test) goes through this path.

2. The static `CLOUD_CODE_TIER_FALLBACKS` dict at the top of the
   module is a safety net for when `/v1/models` is unreachable
   (network failure, Anthropic outage). It was stale — pointed to
   4-5 family while 4-8 was already shipping. Refreshed to 4-8/4-6/4-5
   tier aliases.

3. The introduction question landed on Haiku because `_classify_tier`
   routes short, non-code prompts (<200 chars, no code keywords)
   to Haiku. Haiku 4.5's training data still answers "I am
   Claude 3.5 Sonnet" — a known model self-misidentification, not
   our bug. But for inspector chat, Haiku is a poor default: the
   user sees a worse-than-necessary answer and gets misled by the
   self-ID. Added a `min_tier` floor so the inspector chat path
   defaults to Sonnet (no Haiku) without affecting auto-runner /
   single-task (which still route by classifier and can pick any
   tier).

This file pins:
  - dynamic /v1/models discovery is still the primary path
  - no consumer call site hardcodes a model ID
  - min_tier floor works (haiku → sonnet when min_tier="sonnet")
  - InspectorAgentService.chat_with_cloud_code defaults min_tier="sonnet"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# No hardcoded model IDs in consumer paths
# ---------------------------------------------------------------------------


def test_no_consumer_hardcodes_a_claude_model_id():
    """🛡 Regression guard. None of the cloud_code consumers should
    hardcode a specific `claude-opus-X-Y-DATE` or `claude-sonnet-...`
    string. They must all pass through `pick_model_for_task` /
    `pick_best_model` so the choice stays dynamic when Anthropic
    ships a new revision."""
    root = Path(__file__).resolve().parents[1]
    consumer_files = [
        "app/services/prompt_github_sync.py",       # auto-runner
        "app/services/oversight_service.py",         # single-task
        "app/services/inspector_agent_service.py",   # inspector chat
        "app/api/routes/external_prompts.py",        # verify chain
    ]
    # Anthropic model id pattern: claude-{tier}-{major}-{minor}-{date}
    # or shorter alias claude-{tier}-{major}-{minor}.
    bad_pattern = re.compile(
        r'claude-(opus|sonnet|haiku)-\d[\w\-]*'
    )
    offenders = []
    for rel in consumer_files:
        path = root / rel
        src = path.read_text(encoding="utf-8")
        for lineno, ln in enumerate(src.splitlines(), 1):
            # Comments are fine — they explain context.
            stripped = ln.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue
            m = bad_pattern.search(ln)
            if m:
                offenders.append(f"{rel}:{lineno}: {ln.strip()}")
    assert offenders == [], (
        "consumer files must not hardcode Claude model IDs — they should "
        "use pick_model_for_task / pick_best_model so the choice stays "
        "dynamic. Offenders:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Dynamic discovery is the primary path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pick_best_model_uses_v1_models_for_dynamic_choice(monkeypatch):
    """`pick_best_model` must hit `list_available_models` (which calls
    /v1/models) and pick the newest revision in the tier — not the
    static fallback."""
    from app.services import cloud_code_service as ccs

    fake_models = [
        {"id": "claude-sonnet-4-6-20250929", "created_at": "2025-09-29"},
        {"id": "claude-sonnet-4-7-20251015", "created_at": "2025-10-15"},
        {"id": "claude-sonnet-4-8-20251101", "created_at": "2025-11-01"},  # newest
    ]
    monkeypatch.setattr(
        ccs, "list_available_models",
        AsyncMock(return_value=fake_models),
    )

    model_id, tier, reason = await ccs.pick_best_model(
        [{"role": "user", "content": "x" * 300}],  # forces sonnet
    )
    assert tier == "sonnet"
    # MUST pick the newest revision (4-8), not the fallback (4-6).
    assert model_id == "claude-sonnet-4-8-20251101", (
        f"picker returned {model_id!r} — must pick newest revision in tier"
    )


@pytest.mark.asyncio
async def test_pick_best_model_falls_back_only_when_discovery_empty(monkeypatch):
    """Fallback dict is the safety net, not the primary path. Only
    triggers when /v1/models returns nothing for that tier."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setattr(
        ccs, "list_available_models",
        AsyncMock(return_value=[]),
    )
    model_id, tier, reason = await ccs.pick_best_model(
        [{"role": "user", "content": "x" * 300}],
        tier_hint="sonnet",
    )
    # Now we hit the fallback
    assert "fallback" in reason.lower() or model_id == ccs.CLOUD_CODE_TIER_FALLBACKS["sonnet"]


# ---------------------------------------------------------------------------
# min_tier floor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_min_tier_raises_haiku_to_sonnet(monkeypatch):
    """Short non-code prompt would normally route to Haiku. With
    min_tier='sonnet', it must be raised to Sonnet."""
    from app.services import cloud_code_service as ccs

    fake_models = [
        {"id": "claude-haiku-4-5-20251001", "created_at": "2025-10-01"},
        {"id": "claude-sonnet-4-8-20251101", "created_at": "2025-11-01"},
    ]
    monkeypatch.setattr(
        ccs, "list_available_models",
        AsyncMock(return_value=fake_models),
    )

    # Short prompt → classifier picks haiku
    model_id, tier, _ = await ccs.pick_best_model(
        [{"role": "user", "content": "سلام، خودت رو معرفی کن"}],  # ~26 chars
        min_tier="sonnet",
    )
    assert tier == "sonnet", (
        f"min_tier='sonnet' must lift haiku → sonnet; got tier={tier!r}"
    )
    assert "sonnet" in model_id


@pytest.mark.asyncio
async def test_min_tier_does_not_lower_opus(monkeypatch):
    """min_tier is a floor, not a ceiling. Opus (chosen by heavy
    keyword) must stay Opus."""
    from app.services import cloud_code_service as ccs

    fake_models = [
        {"id": "claude-opus-4-8-20251101", "created_at": "2025-11-01"},
        {"id": "claude-sonnet-4-8-20251101", "created_at": "2025-11-01"},
    ]
    monkeypatch.setattr(
        ccs, "list_available_models",
        AsyncMock(return_value=fake_models),
    )

    # Heavy keyword "refactor" forces opus
    model_id, tier, _ = await ccs.pick_best_model(
        [{"role": "user", "content": "refactor this architecture"}],
        min_tier="sonnet",  # floor, not ceiling
    )
    assert tier == "opus"


# ---------------------------------------------------------------------------
# Inspector chat default is sonnet floor
# ---------------------------------------------------------------------------


def test_inspector_chat_defaults_to_min_tier_sonnet():
    """The inspector chat path must default min_tier='sonnet' so a
    short introduction prompt doesn't trip into Haiku and produce a
    misleading 'I am Claude 3.5 Sonnet' hallucination."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/inspector_agent_service.py"
    ).read_text(encoding="utf-8")
    # The default must appear in the signature of chat_with_cloud_code.
    assert 'min_tier: Optional[str] = "sonnet"' in src, (
        "InspectorAgentService.chat_with_cloud_code must default "
        "min_tier='sonnet' to avoid Haiku on short prompts"
    )


# ---------------------------------------------------------------------------
# Fallback dict is at least up to date
# ---------------------------------------------------------------------------


def test_fallback_dict_uses_current_tier_aliases():
    """The static fallback dict is only used when /v1/models is
    unreachable. It must point at aliases that resolve to current
    families (4-8 opus / 4-6 sonnet / 4-5 haiku at time of writing)
    so a network outage doesn't dump users onto an old generation."""
    from app.services.cloud_code_service import CLOUD_CODE_TIER_FALLBACKS

    # The opus fallback should be at least 4-x.
    assert CLOUD_CODE_TIER_FALLBACKS["opus"].startswith("claude-opus-4-")
    assert CLOUD_CODE_TIER_FALLBACKS["sonnet"].startswith("claude-sonnet-4-")
    assert CLOUD_CODE_TIER_FALLBACKS["haiku"].startswith("claude-haiku-4-")
