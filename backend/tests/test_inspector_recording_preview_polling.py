"""🚨 Inspector recording preview — 409 must trigger polling, not error.

User reported (mode B, "ضبط آزاد"):
   خطا: preview آماده نیست (phase=processing)
   GET /preview → 409
   "قبلا کار میکرد ولی" — used to work, doesn't anymore

The error message is the EXACT response detail from the backend's
preview endpoint when `session.phase != "ready_for_preview"`. Two ways
the frontend can hit this state right after /stop:

  1. Long recordings (the user's was 1m45s) take 30-90s to process
     (transcribe + multimodal vision + prompt synthesis). Render's
     gateway has a 100s request timeout. If processing exceeds that,
     /stop returns prematurely and the next /preview call hits a still-
     processing session.
  2. /stop early-returns if the session is already past
     "recording"/"stopping" (duplicate-click race, retry). The
     early-returned session has phase=processing.

Either way: the UX must POLL until processing finishes (or the session
goes to "errored"), not throw a "preview نیست" error in the user's
face that makes the recording seem lost.

Backend invariants this pins:
  - /preview returns 409 when not ready (existing behavior, must stay
    documented so the frontend can rely on it)
  - /status returns the current phase (so the frontend can detect
    terminal "errored" state and stop polling)

Frontend invariants this pins:
  - fetchPreview polls on 409 (doesn't immediately error)
  - It bails out gracefully on phase=errored (terminal failure)
  - There's an upper time bound so a truly stuck server doesn't hang
    the UI forever
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend/src"


def _read_panel() -> str:
    return (
        _FRONTEND_ROOT / "components/InspectorRecordingPanel.tsx"
    ).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Backend contracts that the frontend polling relies on
# ---------------------------------------------------------------------------


def test_preview_endpoint_returns_409_on_not_ready():
    """The backend MUST return 409 (not 500/200/204) when the session
    isn't ready yet — that's the signal the frontend polls on. Without
    this exact status code, the polling logic can't distinguish
    not-ready-yet from a real error."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/inspector_recording.py"
    ).read_text(encoding="utf-8")
    # Find the get_preview function and verify it uses 409
    idx = src.find("async def get_preview")
    assert idx != -1
    body = src[idx:idx + 1500]
    assert "status_code=409" in body, (
        "preview endpoint must return 409 when not ready — that's the "
        "agreed signal the frontend polls on"
    )
    assert "phase=" in body, (
        "the 409 detail must include the current phase so the frontend "
        "can show progress to the user"
    )


def test_status_endpoint_exposes_phase():
    """The frontend polling needs to detect terminal "errored" state
    via /status (otherwise it would poll forever after a real failure).
    /status must return session.phase in a stable shape."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/inspector_recording.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def get_status")
    assert idx != -1
    body = src[idx:idx + 800]
    assert "to_status_dict" in body, (
        "status endpoint must serialize the session via to_status_dict "
        "so phase is accessible"
    )


# ---------------------------------------------------------------------------
# Frontend polling behavior
# ---------------------------------------------------------------------------


def test_fetch_preview_polls_on_409():
    """🚨 Regression guard: previously fetchPreview did a single fetch
    and threw on 409. Long recordings would always trip this. The fix
    must keep polling on 409, not throw."""
    src = _read_panel()
    idx = src.find("async function fetchPreview")
    assert idx != -1
    body = src[idx:idx + 4000]
    # The 409 path must continue (loop) instead of throwing
    assert "res.status === 409" in body, (
        "fetchPreview must explicitly handle 409 — that's what /preview "
        "returns while processing is still running"
    )
    # Look for a polling loop construct
    assert "while" in body or "setInterval" in body or "POLL_INTERVAL" in body, (
        "fetchPreview must have a polling loop on 409 — not a single fetch"
    )
    # And there must be a delay between polls (no busy-loop)
    assert "setTimeout" in body, (
        "polling must have a setTimeout-based delay so we don't hammer "
        "the server"
    )


def test_fetch_preview_bails_on_errored_phase():
    """If the backend reports phase=errored via /status, polling must
    stop and surface the error — not poll forever."""
    src = _read_panel()
    idx = src.find("async function fetchPreview")
    body = src[idx:idx + 4000]
    assert "errored" in body, (
        "fetchPreview must check for phase=errored as a terminal state, "
        "otherwise it polls forever after a real failure"
    )
    # And it should consult /status (not just /preview) to learn this
    assert "/status" in body, (
        "fetchPreview must cross-check /status during polling — /preview "
        "always returns 409 while processing, so without /status we can't "
        "detect terminal errored state"
    )


def test_fetch_preview_has_max_wait_bound():
    """An upper time bound prevents the UI from hanging forever if the
    server's processing truly hangs (e.g., deadlock in vision call)."""
    src = _read_panel()
    idx = src.find("async function fetchPreview")
    body = src[idx:idx + 4000]
    assert "MAX_POLL_SECONDS" in body or "Date.now() - startedAt" in body, (
        "fetchPreview must have an upper time bound on polling so a "
        "stuck server doesn't hang the UI forever"
    )


def test_fetch_preview_surfaces_progress_to_user():
    """During the (possibly long) poll, the user should see something
    happening — not a frozen UI. We update processingStage with elapsed
    time so they know the system is alive."""
    src = _read_panel()
    idx = src.find("async function fetchPreview")
    body = src[idx:idx + 4000]
    assert "setProcessingStage" in body, (
        "fetchPreview must update processingStage during polling so the "
        "user sees progress (otherwise the UI looks frozen for 30-90s)"
    )
