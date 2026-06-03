"""Fix #3: Cloud Code primary + Gemini fallback for file extraction.

The user pointed out that file extraction (PDF/image/audio/video) was
running through Gemini and costing API credits, while their Cloud Code
OAuth subscription already covers the same workload for visual content.
They asked: can Claude via the OAuth token replace Gemini for the
extraction pipeline, and fall back to Gemini for formats Claude doesn't
support (audio/video)?

The plan they approved:
  - Default extraction model for vision-capable MIMEs (image, PDF) becomes
    `cloud_code` when the user has ticked `file_extraction` in the
    models page.
  - Audio/video MIMEs always use Gemini (Claude doesn't support them).
  - If a cloud_code extraction call fails (subscription cap, network),
    auto-fall back to the best non-OAuth multimodal model so the user
    never sees an extraction outage.

What this file pins:

1. `pick_best_extraction_model` returns `cloud_code` for image MIMEs
   when the helper says `file_extraction` is enabled.
2. It does NOT return `cloud_code` for audio/video MIMEs (Claude has
   no audio/video capability, so it must drop through to Gemini).
3. It does NOT return `cloud_code` when the helper says
   `file_extraction` is disabled (legacy behavior preserved).
4. The MODEL_REGISTRY entry now declares vision + document capabilities
   so the picker's capability filter accepts cloud_code for the right
   MIMEs.
5. `_ai_extract_text` has a model_id == "cloud_code" short-circuit that
   routes through cloud_code_message with content blocks.
6. The `_extract_via_cloud_code` helper builds the correct Anthropic
   content-block shapes for image and document.
7. `file_extraction` is now in CLOUD_CODE_PREFERRED_FOR_KEYS so the UI
   surfaces the toggle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# registry entry now has vision capabilities
# ---------------------------------------------------------------------------


def test_cloud_code_registry_entry_has_vision_capabilities():
    from app.core.models_registry import MODEL_REGISTRY, ModelCapability

    entry = MODEL_REGISTRY["cloud_code"]
    cap_set = set(entry.capabilities)
    assert ModelCapability.VISION in cap_set, (
        "cloud_code must declare VISION for the picker's capability filter "
        "to accept it for image MIMEs"
    )
    assert ModelCapability.DOCUMENT_UNDERSTANDING in cap_set, (
        "cloud_code must declare DOCUMENT_UNDERSTANDING for PDF support"
    )
    # Audio/video intentionally NOT here — Claude doesn't support them.
    assert ModelCapability.AUDIO_UNDERSTANDING not in cap_set
    assert ModelCapability.VIDEO_UNDERSTANDING not in cap_set


# ---------------------------------------------------------------------------
# 4 + 1 preferred_for keys
# ---------------------------------------------------------------------------


def test_file_extraction_key_added_to_preferred_for_keys():
    from app.models.ai_profile import (
        CLOUD_CODE_PREFERRED_FOR_KEYS,
        AVAILABLE_TASK_TYPES,
    )

    assert "file_extraction" in CLOUD_CODE_PREFERRED_FOR_KEYS, (
        "file_extraction must be in CLOUD_CODE_PREFERRED_FOR_KEYS so the "
        "helper consults it and the UI shows it"
    )
    ids = {t["id"] for t in AVAILABLE_TASK_TYPES}
    assert "file_extraction" in ids, (
        "AVAILABLE_TASK_TYPES must include the new key"
    )


# ---------------------------------------------------------------------------
# picker picks cloud_code for image MIMEs when helper says yes
# ---------------------------------------------------------------------------


def test_picker_returns_cloud_code_for_image_when_helper_enabled(monkeypatch):
    """The happy path: user enabled file_extraction on cloud_code,
    picker must short-circuit and return cloud_code for image MIMEs."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    # Pretend the helper says yes for file_extraction:
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: key == "file_extraction",
    )

    picked = mr.pick_best_extraction_model("image/png")
    assert picked is not None
    assert picked.id == "cloud_code"


def test_picker_returns_cloud_code_for_pdf_when_helper_enabled(monkeypatch):
    """Same for PDF — Claude supports document content blocks via OAuth."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: key == "file_extraction",
    )

    picked = mr.pick_best_extraction_model("application/pdf")
    assert picked is not None
    assert picked.id == "cloud_code"


def test_picker_does_not_return_cloud_code_for_audio(monkeypatch):
    """Claude doesn't support audio. Picker must drop through to the
    legacy ranking (Gemini wins for audio) regardless of the helper."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    # Helper says yes — but capability gate must prevent cloud_code anyway.
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: True,
    )

    picked = mr.pick_best_extraction_model("audio/ogg")
    # The picker may return None (no audio model available in test env),
    # but it absolutely must not return cloud_code.
    assert picked is None or picked.id != "cloud_code"


def test_picker_does_not_return_cloud_code_for_video(monkeypatch):
    """Same for video — Gemini is the only practical option, not cloud_code."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: True,
    )

    picked = mr.pick_best_extraction_model("video/mp4")
    assert picked is None or picked.id != "cloud_code"


def test_picker_skips_cloud_code_when_helper_says_off(monkeypatch):
    """User left file_extraction unticked → legacy Gemini path."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: False,
    )

    picked = mr.pick_best_extraction_model("image/png")
    # cloud_code must not be picked when helper says off
    assert picked is None or picked.id != "cloud_code"


# ---------------------------------------------------------------------------
# _ai_extract_text routes cloud_code to the OAuth path
# ---------------------------------------------------------------------------


def test_extract_text_special_cases_cloud_code():
    """Source check — _ai_extract_text must detect model_id == 'cloud_code'
    and call the OAuth helper, not ai_manager.generate (which would fail
    silently because cloud_code isn't in _services)."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_extraction.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def _ai_extract_text")
    assert idx != -1
    # slice to next async def
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert 'model_id == "cloud_code"' in body
    assert "_extract_via_cloud_code" in body
    # fallback path must remain so a cloud_code outage doesn't break extraction
    assert "falling back to non-OAuth multimodal model" in body or "fallback" in body.lower()


def test_extract_via_cloud_code_builds_image_content_block():
    """Source check — the helper must build the Anthropic content-block
    shape for images (type: image, source: base64 + media_type + data)."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_extraction.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def _extract_via_cloud_code")
    assert idx != -1
    body = src[idx:idx + 4000]
    assert '"type": "image"' in body
    assert '"type": "document"' in body
    assert '"base64"' in body
