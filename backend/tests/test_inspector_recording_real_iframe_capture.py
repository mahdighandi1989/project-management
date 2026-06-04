"""🎬 Inspector recording mode A — REAL iframe capture (not slideshow).

History of the user's frustration:
  v0: mode A produced an animated WebP → Telegram sent it as a sticker
      (one frame). User: "ویدیو نیست، عکس استیکر".
  v1: I built MP4/GIF from frames. Still no audio, no smooth motion, no
      visible interactions. User: "این کار تو یه جور فریب بود" — every
      output was still a slideshow synthesized from periodic screenshots.

Root architectural fix (this commit):
  Mode A now captures the iframe as REAL video using
  getDisplayMedia({preferCurrentTab: true}) + a canvas that crops the
  resulting tab stream to just the iframe's bounding rect every frame.
  The canvas's captureStream(30) goes through MediaRecorder exactly
  like mode B — same .webm chunks via the same /video-chunk endpoint.

Invariants this file pins:

  1. Backend: append_video_chunk accepts BOTH modes (was mode-B-only —
     that was the architectural lock preventing real mode-A video).
  2. Finalize: both modes use _assemble_video_from_chunks first;
     slideshow synthesis is only a last-resort fallback for legacy
     sessions with no chunks.
  3. Frontend (source-grep): InspectorRecordingPanel actually calls
     getDisplayMedia + draws to a canvas in mode A. No bandage allowed.
  4. Frontend: the cropping math uses iframe.getBoundingClientRect()
     scaled by window.innerWidth/innerHeight (correct mapping for
     tab-capture). If a refactor breaks this, video will be misaligned.
  5. Frontend: cropping cleanup releases the source video + canvas
     stream so the stream doesn't leak after stopRecording.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend/src"


def _read_panel() -> str:
    return (
        _FRONTEND_ROOT / "components/InspectorRecordingPanel.tsx"
    ).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Backend: append_video_chunk no longer mode-B-only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_append_video_chunk_accepts_mode_a():
    """The architectural lock that blocked real mode-A video MUST be
    gone. Before this, the endpoint raised 'video chunks فقط در حالت B'
    — and the frontend's only mode-A path was screenshot polling."""
    from app.services.inspector_recording_service import (
        get_inspector_recording_service,
    )
    svc = get_inspector_recording_service()
    # Create a tiny in-memory session and force mode A
    sess = await svc.start_session(
        project_id="test_proj", project_full_name="test/proj", mode="A",
        target_fps=2,
    )
    try:
        # Should NOT raise the legacy "mode B only" error
        await svc.append_video_chunk(
            sess.session_id, seq=0, chunk_bytes=b"fake-webm-bytes",
        )
        assert sess.video_chunks_count == 1
        # Verify the chunk landed on disk
        chunks = list(sess.video_dir.glob("chunk_*.webm"))
        assert len(chunks) == 1
    finally:
        # Best-effort cleanup
        try:
            shutil.rmtree(sess.session_dir, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 2. Finalize: video chunks path is used for BOTH modes
# ---------------------------------------------------------------------------


def test_finalize_source_uses_chunks_for_both_modes():
    """Source check — the finalize pipeline must NOT branch by mode for
    the primary video assembly. Both modes go through
    _assemble_video_from_chunks first. Slideshow synthesis is fallback
    only for legacy sessions (with no chunks)."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/inspector_recording_finalize.py"
    ).read_text(encoding="utf-8")
    # The old `if session.mode == "B":` mode-discriminating branch must
    # be gone for the primary video assembly.
    # Find the Stage 2 block
    idx = src.find("# ------- Stage 2: assemble media")
    assert idx != -1
    body = src[idx:idx + 3000]
    # Look for assemble_video_from_chunks being called unconditionally
    assert "_assemble_video_from_chunks(session.video_dir)" in body
    # The slideshow synthesizer must be inside an `elif session.mode == "A"`
    # legacy-fallback branch, not the primary path.
    assert "elif session.mode == \"A\"" in body, (
        "slideshow synthesis must be a legacy fallback, not the primary "
        "mode-A path. Otherwise we're back to producing a screenshot "
        "slideshow instead of real video."
    )


# ---------------------------------------------------------------------------
# 3. Frontend: mode A actually calls getDisplayMedia + canvas crop
# ---------------------------------------------------------------------------


def test_mode_a_uses_get_display_media():
    """The frontend mode-A path must call getDisplayMedia. The previous
    architecture only called this for mode B. If a refactor reverts to
    `startScreenshotPolling`-only for mode A, the user is back to
    slideshow hell."""
    src = _read_panel()
    # Locate the mode A branch (the else of mode === 'B')
    # The mode A block is documented with the "REAL iframe-only video"
    # marker — pin the marker so a refactor can't quietly delete it.
    assert "REAL iframe-only video" in src, (
        "the mode-A real-capture marker must remain — without it, a "
        "refactor could silently restore the screenshot-slideshow path"
    )
    assert "getDisplayMedia" in src
    # Verify getDisplayMedia is invoked more than once — once for mode B
    # AND once for mode A (the new path).
    assert src.count("getDisplayMedia") >= 2, (
        "mode A must invoke getDisplayMedia independently from mode B"
    )


def test_mode_a_crops_with_canvas():
    """The crop step must use a canvas + drawImage from a source video.
    Without the crop, we'd be sending the entire tab (which is mode B's
    behavior). Mode A's promise is 'iframe only'."""
    src = _read_panel()
    # Find the mode-A block (after the 'REAL iframe-only video' marker)
    idx = src.find("REAL iframe-only video")
    body = src[idx:idx + 6000]
    assert "document.createElement('canvas')" in body or 'createElement("canvas")' in body, (
        "mode A must create a canvas to crop the iframe out of the tab stream"
    )
    assert "drawImage" in body, (
        "the rAF loop must call drawImage to paint the iframe region"
    )
    assert "canvas.captureStream" in body or ".captureStream(" in body, (
        "the canvas must expose a captureStream so MediaRecorder can "
        "record the iframe-only video"
    )


def test_mode_a_uses_bounding_rect_for_crop_math():
    """The mapping from tab-pixel space to iframe-pixel space is critical:
    if the formula is wrong, the recorded video shows the wrong part of
    the tab. The fix uses getBoundingClientRect() / window.innerWidth."""
    src = _read_panel()
    idx = src.find("REAL iframe-only video")
    body = src[idx:idx + 6000]
    assert "getBoundingClientRect" in body, (
        "crop math must read iframe.getBoundingClientRect() each frame "
        "so panel resize / scroll is handled live"
    )
    assert "window.innerWidth" in body and "window.innerHeight" in body, (
        "tab-stream → iframe-pixel mapping uses window.innerWidth/Height "
        "as the divisor (Chrome tab capture matches the viewport, not "
        "the screen)"
    )


def test_mode_a_uploads_to_video_chunk_endpoint():
    """Mode A must upload its captured webm chunks to the same
    `/video-chunk` endpoint mode B uses — that's the unified backend
    contract. If it goes anywhere else, the finalize pipeline can't
    pick it up."""
    src = _read_panel()
    idx = src.find("REAL iframe-only video")
    body = src[idx:idx + 9000]
    assert "/video-chunk" in body, (
        "mode A must upload via the /video-chunk endpoint (same as mode B). "
        "Going through a separate path would re-fork the architecture."
    )


def test_mode_a_cleanup_releases_crop_resources():
    """cleanupStreams must release ALL the new mode-A resources
    (source video, canvas, crop stream, rAF). Otherwise stopping a
    recording leaks an active getDisplayMedia stream and the browser
    keeps showing the 'this tab is being shared' indicator forever."""
    src = _read_panel()
    idx = src.find("function cleanupStreams")
    assert idx != -1
    body = src[idx:idx + 2000]
    # Each new ref must be cleared in cleanup
    for ref_name in (
        "sourceVideoRef",
        "cropCanvasRef",
        "cropStreamRef",
        "rafRef",
        "cropStoppedRef",
    ):
        assert ref_name in body, (
            f"cleanupStreams must release {ref_name} — without it, the "
            "browser keeps the screen-share indicator after stop"
        )
    assert "cancelAnimationFrame" in body, (
        "the rAF loop must be cancelled on cleanup or it keeps drawing "
        "into a torn-down canvas"
    )


# ---------------------------------------------------------------------------
# 4. PostMessage bridge for interactions must STILL be attached in mode A
# ---------------------------------------------------------------------------


def test_mode_a_still_attaches_post_message_bridge():
    """Even with real video capture, the metadata pipe for in-iframe
    interactions must remain — that's how clicks/scrolls become
    structured events in the extractor (in addition to being visually
    captured in the video)."""
    src = _read_panel()
    idx = src.find("REAL iframe-only video")
    body = src[idx:idx + 10000]
    assert "attachPostMessageBridge" in body, (
        "interactions bridge must still be attached in the new mode-A "
        "path — otherwise structured event data is lost"
    )
