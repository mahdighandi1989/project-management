"""Audit follow-ups from independent review of c5523f6.

The independent reviewer flagged three real issues:

1. 🚨 CRITICAL — fallback chain doesn't actually work
   When `_ai_extract_text`'s cloud_code path raised (subscription cap,
   rate limit, network), the recovery code calls
   `pick_best_extraction_model(..., require_api_key=True)` expecting
   Gemini back. But the cloud_code short-circuit at the top of the
   picker ignored `require_api_key` and re-picked cloud_code. The
   recovery then saw `_fallback.id == "cloud_code"` and re-raised the
   original error → user-visible outage on every cloud_code failure.

   Fix: make the short-circuit honor `require_api_key=True`. When that
   flag is set, the caller is explicitly asking for an API-key-backed
   model — cloud_code's OAuth provider doesn't qualify.

2. ⚠ MEDIUM — hardcoded media_type=image/png
   `_extract_via_cloud_code` blindly stamped every image as image/png,
   even for JPEG/WebP/GIF inputs. Anthropic tolerates it most of the
   time but technically incorrect and known to reject some MIMEs.

   Fix: thread the actual MIME from the caller (where it's already
   in scope at oversight_extraction.py:1472) through to the content
   block. Backward-compat default stays image/png.

3. ⚠ MEDIUM — source-of-truth drift between backend/frontend
   The list of cloud_code consumer keys is duplicated in three places:
     - backend `CLOUD_CODE_PREFERRED_FOR_KEYS` (Python list)
     - backend `AVAILABLE_TASK_TYPES` (dict list)
     - frontend `CLOUD_CODE_TASK_KEYS` (TypeScript Set)
   No test asserted they stay in sync — a future contributor adding
   a key to only one would silently break the UI/wiring contract.

   Fix: cross-file sync test that reads both source files and asserts
   the sets match exactly.

These tests pin the fixes at the source/behavior level so neither can
regress quietly.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Fix #1 — fallback chain actually works
# ---------------------------------------------------------------------------


def test_picker_short_circuit_respects_exclude_cloud_code_flag(monkeypatch):
    """🚨 The critical fix. When exclude_cloud_code=True (set by the
    fallback path in _ai_extract_text), the cloud_code short-circuit
    must be SKIPPED so the fallback lands on Gemini."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: True,
    )

    picked = mr.pick_best_extraction_model(
        "image/png", exclude_cloud_code=True,
    )
    # cloud_code MUST NOT be returned. Other models may not qualify in
    # test env, but cloud_code must be excluded.
    assert picked is None or picked.id != "cloud_code"


def test_picker_returns_cloud_code_for_default_caller(monkeypatch):
    """🚨🚨 THE REGRESSION THIS WHOLE COMMIT EXISTS TO PREVENT.
    The production caller at oversight_extraction.py:1303 calls the
    picker with NO require_api_key or exclude_cloud_code argument:
        pick_best_extraction_model(mime, preferred_model_id=..., db_enabled_ids=...)

    Previously, the cloud_code short-circuit was gated by `not require_api_key`,
    and require_api_key defaulted to True — so the default call NEVER
    returned cloud_code. The whole c5523f6 commit (extraction routing)
    was silently dead code; Gemini API budget was still burned for
    image/PDF extraction.

    This test calls the picker with NO override kwargs (mimicking the
    real production call) and asserts cloud_code IS returned for an
    image MIME when the helper says yes."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: True,
    )

    # NO require_api_key, NO exclude_cloud_code — defaults like production
    picked = mr.pick_best_extraction_model("image/png")
    assert picked is not None
    assert picked.id == "cloud_code", (
        f"production default call must return cloud_code (got {picked.id!r}). "
        f"if this test fails, the feature toggle in the models page is a no-op."
    )


def test_picker_short_circuit_still_works_when_require_api_key_false(monkeypatch):
    """Legacy regression guard kept for safety. The flag still works
    even though it's no longer the primary gating mechanism."""
    from app.core import models_registry as mr

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: True,
    )

    picked = mr.pick_best_extraction_model("image/png", require_api_key=False)
    assert picked is not None
    assert picked.id == "cloud_code"


def test_extraction_fallback_calls_picker_with_exclude_cloud_code():
    """Source check — the fallback path in _ai_extract_text must pass
    exclude_cloud_code=True so the picker excludes cloud_code. Otherwise
    the fallback re-picks cloud_code and re-raises."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_extraction.py"
    ).read_text(encoding="utf-8")
    # Locate the cloud_code fallback block
    idx = src.find('logger.warning(\n                f"_ai_extract_text: cloud_code path failed')
    assert idx != -1, "fallback block not found — test stale"
    rest = src[idx:idx + 2000]
    # Must call _pick with exclude_cloud_code=True
    assert "exclude_cloud_code=True" in rest, (
        "fallback must call picker with exclude_cloud_code=True so "
        "cloud_code is excluded (otherwise it re-picks cloud_code "
        "and re-raises the original error)"
    )


# ---------------------------------------------------------------------------
# Fix #2 — media_type uses actual mime
# ---------------------------------------------------------------------------


def test_extract_via_cloud_code_uses_image_mime_param():
    """_extract_via_cloud_code must use the image_mime parameter for
    the content block's media_type instead of hardcoding image/png."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_extraction.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def _extract_via_cloud_code")
    assert idx != -1
    body = src[idx:idx + 3000]
    # The function signature must accept image_mime
    assert "image_mime: str" in body
    # And the image content block must use it, not the hardcoded literal
    assert '"media_type": image_mime' in body, (
        "image content block must use the image_mime param, not "
        "the previous hardcoded 'image/png' literal"
    )


def test_ai_extract_text_accepts_image_mime():
    """The wrapper function must expose image_mime as a parameter so
    callers can pass the actual MIME they have in scope."""
    from app.services.oversight_extraction import _ai_extract_text
    import inspect

    sig = inspect.signature(_ai_extract_text)
    assert "image_mime" in sig.parameters
    # Backward-compat default
    assert sig.parameters["image_mime"].default == "image/png"


def test_caller_at_image_branch_passes_actual_mime():
    """The call site in _run_extraction (image branch) must pass
    image_mime=mime so the actual MIME flows through."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_extraction.py"
    ).read_text(encoding="utf-8")
    # Look for the image-branch call with image_mime=mime
    assert "image_mime=mime" in src, (
        "_run_extraction must pass image_mime=mime to _ai_extract_text "
        "for image attachments (otherwise the cloud_code content block "
        "mis-labels JPEG/WebP/GIF as PNG)"
    )


# ---------------------------------------------------------------------------
# Fix #3 — backend/frontend cloud_code key sync
# ---------------------------------------------------------------------------


def _extract_frontend_cloud_code_keys() -> set:
    """Parse the JavaScript Set literal from models/page.tsx."""
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/models/page.tsx"
    ).read_text(encoding="utf-8")
    # Match: const CLOUD_CODE_TASK_KEYS = new Set([ ... ]);
    m = re.search(
        r"const\s+CLOUD_CODE_TASK_KEYS\s*=\s*new\s+Set\(\s*\[(.*?)\]\s*\)",
        src,
        re.DOTALL,
    )
    assert m, "CLOUD_CODE_TASK_KEYS literal not found in frontend"
    body = m.group(1)
    # Extract quoted strings (single or double quotes)
    return set(re.findall(r"['\"]([^'\"]+)['\"]", body))


def test_backend_and_frontend_cloud_code_keys_match_exactly():
    """🛡 Drift guard. The list of cloud_code consumer keys exists in
    three places; if any drifts, the UI silently disconnects from the
    backend wiring. This test reads both source files at runtime and
    asserts the sets match.

    If you add a new key, you must add it to ALL THREE:
      - AVAILABLE_TASK_TYPES (backend, ai_profile.py)
      - CLOUD_CODE_PREFERRED_FOR_KEYS (backend, ai_profile.py)
      - CLOUD_CODE_TASK_KEYS (frontend, models/page.tsx)
    """
    from app.models.ai_profile import (
        AVAILABLE_TASK_TYPES,
        CLOUD_CODE_PREFERRED_FOR_KEYS,
    )

    backend_keys = set(CLOUD_CODE_PREFERRED_FOR_KEYS)
    frontend_keys = _extract_frontend_cloud_code_keys()

    # Source-of-truth 1 vs Source-of-truth 3
    assert backend_keys == frontend_keys, (
        f"backend CLOUD_CODE_PREFERRED_FOR_KEYS and frontend "
        f"CLOUD_CODE_TASK_KEYS have drifted!\n"
        f"  in backend only: {backend_keys - frontend_keys}\n"
        f"  in frontend only: {frontend_keys - backend_keys}"
    )

    # Source-of-truth 1 vs Source-of-truth 2
    task_type_ids = {t["id"] for t in AVAILABLE_TASK_TYPES}
    missing_from_task_types = backend_keys - task_type_ids
    assert not missing_from_task_types, (
        f"CLOUD_CODE_PREFERRED_FOR_KEYS contains keys not declared in "
        f"AVAILABLE_TASK_TYPES (UI won't render them): "
        f"{missing_from_task_types}"
    )
