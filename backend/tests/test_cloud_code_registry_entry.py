"""Stage 1 of the Cloud Code centralization: registry entry.

User reported feature is currently scattered across multiple files
(auto-runner, per-task button, inspector chat engine, creator engine).
Plan is to centralize through the existing models page (the same one
that lists GPT-4o, Claude Opus, etc.).

This stage adds a `cloud_code` entry to MODEL_REGISTRY and 4 task-type
keys to AVAILABLE_TASK_TYPES so that the existing ModelSettings DB row
(which already has preferred_for: List[str]) can drive routing.

NOTHING is wired through to consumers yet — that's stage 3. This stage
just ensures the entry exists, GET /models would return it, and the
4 preferred_for keys are documented in one place.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Provider enum gets a new value
# ---------------------------------------------------------------------------


def test_cloud_code_provider_enum_added():
    from app.core.models_registry import ModelProvider

    assert hasattr(ModelProvider, "CLOUD_CODE")
    assert ModelProvider.CLOUD_CODE.value == "cloud_code"


# ---------------------------------------------------------------------------
# MODEL_REGISTRY has the entry
# ---------------------------------------------------------------------------


def test_cloud_code_entry_present_in_registry():
    from app.core.models_registry import MODEL_REGISTRY, ModelProvider

    assert "cloud_code" in MODEL_REGISTRY, (
        "MODEL_REGISTRY must include `cloud_code` so the models page "
        "and /api/models endpoint surface it as a manageable row"
    )
    entry = MODEL_REGISTRY["cloud_code"]
    assert entry.id == "cloud_code"
    assert entry.provider == ModelProvider.CLOUD_CODE
    # Cost is zero — this is a subscription, not metered API
    assert entry.cost_per_1k_tokens == 0.0


def test_cloud_code_entry_enabled_by_default():
    """If the user hasn't touched ModelSettings, behavior must match
    today's (Cloud Code works everywhere it's set up). Setting
    enabled=True in the registry achieves that default."""
    from app.core.models_registry import MODEL_REGISTRY

    assert MODEL_REGISTRY["cloud_code"].enabled is True


def test_cloud_code_entry_has_code_and_reasoning_capabilities():
    """Capability list drives where the model can be picked. Cloud Code
    is primarily for code tasks + reasoning; vision/image-gen are not
    its strengths so they're intentionally not listed."""
    from app.core.models_registry import MODEL_REGISTRY, ModelCapability

    caps = MODEL_REGISTRY["cloud_code"].capabilities
    assert ModelCapability.CODE in caps
    assert ModelCapability.REASONING in caps
    # explicitly NOT image-generation / vision (Cloud Code doesn't do those well)
    assert ModelCapability.IMAGE_GENERATION not in caps


# ---------------------------------------------------------------------------
# preferred_for task type keys
# ---------------------------------------------------------------------------


def test_initial_cloud_code_task_types_defined():
    """The user originally picked 4 consumers (auto-runner, single-task,
    inspector, creator). A later fix added `file_extraction` as a 5th.
    All of them must be present in AVAILABLE_TASK_TYPES and in the
    CLOUD_CODE_PREFERRED_FOR_KEYS constant."""
    from app.models.ai_profile import AVAILABLE_TASK_TYPES, CLOUD_CODE_PREFERRED_FOR_KEYS

    ids = {t["id"] for t in AVAILABLE_TASK_TYPES}
    initial = {
        "claude_auto_runner",
        "claude_single_task",
        "inspector_cloud_code",
        "creator_engine",
    }
    assert initial.issubset(ids), (
        f"AVAILABLE_TASK_TYPES missing one of {initial - ids} — these are "
        "the original 4 keys the consumers check via preferred_for"
    )
    # CLOUD_CODE_PREFERRED_FOR_KEYS is the single source of truth for the
    # full set (initial 4 + any added later). It must be a superset of the
    # initial 4.
    assert initial.issubset(set(CLOUD_CODE_PREFERRED_FOR_KEYS))


def test_existing_task_types_not_broken():
    """A regression guard — the existing task types (chat, code_generation,
    etc.) must remain so existing model settings keep working."""
    from app.models.ai_profile import AVAILABLE_TASK_TYPES

    ids = {t["id"] for t in AVAILABLE_TASK_TYPES}
    for old_key in (
        "all", "chat", "analysis", "code_generation", "code_review",
        "documentation", "debugging", "refactoring", "testing",
        "image_analysis", "research",
    ):
        assert old_key in ids, (
            f"existing task type `{old_key}` got dropped — would break "
            "any ModelSettings rows that reference it"
        )


# ---------------------------------------------------------------------------
# get_model() helper picks up the new entry
# ---------------------------------------------------------------------------


def test_get_model_returns_cloud_code_entry():
    from app.core.models_registry import get_model

    m = get_model("cloud_code")
    assert m is not None
    assert m.id == "cloud_code"
    assert m.name == "Cloud Code (Claude OAuth)"
