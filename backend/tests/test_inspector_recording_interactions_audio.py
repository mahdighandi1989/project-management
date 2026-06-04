"""🚨 Inspector recording (mode A) — interaction bridge wire-format.

User-reported regression (after the iframe-mode video fix):
"تعاملات و صدا رو کامل و درست استخراج نکرده بود"

Root cause for INTERACTIONS:
  - `InspectorBridge.tsx` (inside the recorded iframe) emits postMessage
    events with `type: "inspector-bridge-event"` + an `action` field.
  - `InspectorRecordingPanel.tsx` (the recorder, in the parent window)
    was filtering for `d.__inspector_event` — a flag the bridge has
    NEVER sent. Every interaction was silently dropped.
  - Result: mode A recordings always had zero interactions, even though
    the bridge and the panel both ran fine.

The fix in `attachPostMessageBridge` now accepts BOTH:
  (a) the legacy `{__inspector_event: true, ...}` flag (no current
      caller, but kept for compatibility)
  (b) the actual bridge shape `{type: "inspector-bridge-event",
      action, elementInfo, position, pageUrl, level, source, ...}`

Root cause for AUDIO (UX-level):
  - When `getUserMedia({audio: true})` returned no live tracks (mic
    permission denied, no mic plugged in), the recorder silently
    skipped audio. User saw the mic checkbox ticked, recorded for
    minutes, then got an empty transcript with no warning.
  - Fix: surface a clear errorMsg explaining mode A can only capture
    the mic (iframe security blocks system audio) so the user can
    cancel + grant permission BEFORE the long recording.

These tests pin both fixes at the source level so a future refactor
can't quietly drop them.
"""

from __future__ import annotations

from pathlib import Path


_FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend/src"


def _read(rel: str) -> str:
    return (_FRONTEND_ROOT / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Bridge sender shape — InspectorBridge MUST emit "inspector-bridge-event"
# ---------------------------------------------------------------------------


def test_inspector_bridge_emits_inspector_bridge_event_type():
    """If anyone refactors the bridge to emit a different `type` string,
    this test catches it — otherwise the recorder won't recognise it."""
    src = _read("app/InspectorBridge.tsx")
    assert '"inspector-bridge-event"' in src, (
        "InspectorBridge must emit messages with type='inspector-bridge-event' "
        "— that's the shape the recorder listens for"
    )


# ---------------------------------------------------------------------------
# 2. Recorder listener — InspectorRecordingPanel MUST accept that shape
# ---------------------------------------------------------------------------


def test_recorder_accepts_inspector_bridge_event_type():
    """🚨 the actual bug: panel was filtering for `__inspector_event` and
    dropping every event the bridge sent. The fix must accept the bridge's
    actual `type === 'inspector-bridge-event'` shape."""
    src = _read("components/InspectorRecordingPanel.tsx")
    assert "'inspector-bridge-event'" in src, (
        "recorder listener must check for type === 'inspector-bridge-event' "
        "or every mode-A iframe interaction is silently dropped"
    )


def test_recorder_listener_in_post_message_bridge_function():
    """The acceptance check must live inside attachPostMessageBridge
    (where the recorder filters incoming postMessage events). If a
    refactor moves it elsewhere, this guard prevents silent regression."""
    src = _read("components/InspectorRecordingPanel.tsx")
    idx = src.find("function attachPostMessageBridge")
    assert idx != -1, "attachPostMessageBridge must exist"
    # Slice from this function to the next top-level function/EOF
    body = src[idx:idx + 3000]
    assert "'inspector-bridge-event'" in body, (
        "the type-check must live in attachPostMessageBridge — otherwise "
        "the recorder won't match the bridge's protocol"
    )
    # And it must NOT only check the old __inspector_event flag — that
    # was the bug. Both forms acceptable, but the new form is required.
    assert "isInspectorEvent" in body or "inspector-bridge-event" in body


def test_recorder_extracts_action_field_from_bridge_message():
    """The bridge sends `action: 'click' | 'input' | 'scroll' | ...`,
    NOT `type` (which is the protocol marker). The recorder must map
    `action` to its event log so the backend extractor sees meaningful
    interaction types (otherwise every event would be logged as
    'inspector-bridge-event' — useless)."""
    src = _read("components/InspectorRecordingPanel.tsx")
    idx = src.find("function attachPostMessageBridge")
    body = src[idx:idx + 3000]
    assert "d.action" in body, (
        "recorder must read d.action from the bridge message — that's the "
        "actual click/input/scroll discriminator. Storing d.type would just "
        "label every event 'inspector-bridge-event'."
    )


# ---------------------------------------------------------------------------
# 3. Audio UX — no more silent failures
# ---------------------------------------------------------------------------


def test_audio_silent_fail_surfaces_warning_to_user():
    """When no live audio tracks are detected, the recorder must surface
    a visible warning (setErrorMsg). Previously it only console.info'd
    and the user discovered the silent transcript hours later."""
    src = _read("components/InspectorRecordingPanel.tsx")
    # Find the hasRealAudio guard
    idx = src.find("hasRealAudio")
    assert idx != -1
    body = src[idx:idx + 1500]
    # The fix must call setErrorMsg in the no-audio branch
    assert "setErrorMsg" in body, (
        "the no-live-audio branch must call setErrorMsg so the user gets "
        "a visible warning — not just a silent console.info"
    )
    # And the warning must specifically mention مجوز میکروفون / mic
    # permission so the user knows the action item.
    assert "میکروفون" in body, (
        "the warning must mention میکروفون so the user knows to check "
        "browser mic permissions"
    )
