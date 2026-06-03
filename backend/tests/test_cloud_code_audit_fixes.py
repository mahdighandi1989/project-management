"""Post-stage audit fixes for the Cloud Code centralization.

After stages 1-4 shipped, an audit pass found one UX bug:

The /models and /models/providers endpoints determine `is_available`
by checking whether the provider is in `ai_manager.get_available_providers()`.
That list comes from `ai_manager._services`, which only includes providers
that have an API key configured (openai, claude-via-api-key, gemini, etc.).
`cloud_code` is not in there because Cloud Code uses an OAuth subscription
token, not a metered API key.

Without the fix, the Cloud Code row in the models page would always show
the gray "unavailable" dot — even when the user has CLAUDE_CODE_OAUTH_TOKEN
set in env. Confusing UX: user disables Cloud Code thinking it's already
broken, when actually it works fine.

These tests pin the fix: when provider == "cloud_code", availability is
determined by `cloud_code_is_configured()` (env check), not by the
ai_manager service registry.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _read(rel: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / rel
    ).read_text(encoding="utf-8")


def test_list_models_routes_cloud_code_availability_to_env_check():
    """The main /models endpoint must short-circuit availability for
    cloud_code through cloud_code_is_configured(). Source-level pin so
    a future refactor doesn't accidentally drop the override."""
    src = _read("app/api/routes/models.py")
    # The cloud_code-specific override must appear after the generic
    # availability check inside list_models.
    idx = src.find("@router.get(\"\", response_model=List[ModelInfo])")
    assert idx != -1
    rest = src[idx:idx + 3500]
    assert 'model_provider == "cloud_code"' in rest, (
        "list_models must check provider == 'cloud_code' to override "
        "is_available with the env-based check"
    )
    assert "cloud_code_is_configured" in rest, (
        "list_models must call cloud_code_is_configured for the override"
    )


def test_providers_endpoint_routes_cloud_code_availability_to_env_check():
    """The /providers endpoint feeds the colored stat cards at the top
    of the models page. Same fix needs to apply so the Cloud Code card
    shows the green check when the token is set."""
    src = _read("app/api/routes/models.py")
    idx = src.find("def list_providers")
    assert idx != -1
    body = src[idx:idx + 2500]
    assert "cloud_code_is_configured" in body, (
        "list_providers must use cloud_code_is_configured for the cloud_code "
        "provider's available flag"
    )


def test_get_single_model_routes_cloud_code_availability_to_env_check():
    """The single-model GET (used when frontend wants details for one
    row) needs the same override."""
    src = _read("app/api/routes/models.py")
    # Count all `cloud_code_is_configured` references — should be ≥3
    # (list_models, list_providers, single-model-get).
    n_refs = src.count("cloud_code_is_configured")
    assert n_refs >= 3, (
        f"expected ≥3 cloud_code_is_configured references in models.py "
        f"(list, providers, get-by-id); found {n_refs}"
    )
