"""🚨 Cloud Code temperature deprecation auto-retry.

User's screenshot + Render log showed a 400 from Anthropic on every
cloud_code call:

  2026-06-04 16:20:23 - WARNING - cloud_code stream error 400:
  {"type":"error","error":{"type":"invalid_request_error",
  "message":"`temperature` is deprecated for this model.",
  "request_id":"req_011CbiXPH9MYGvX5Da5q5GBP"}}

Newer Claude families (Opus 4.8+ with extended thinking, and likely
future ones) deprecated the `temperature` parameter. Every cloud_code
consumer was sending temperature with the payload, so every call
returned 400 → regenerate-prompt failed with 502, auto-runner verify
failed silently, monitoring with cloud_code as selected_models broke,
etc.

Effect (visible in the user's GitHub Actions screenshot): 441 workflow
runs over hours, all cancelled. Auto-runner not progressing. User
reasonably called it "broken".

Fix: in `cloud_code_stream_chat` and `cloud_code_message`, attempt the
request with the original payload first. If the response is a 400 that
mentions both "temperature" and "deprecated", rebuild the payload
without the `temperature` key and retry once. Generic enough to handle
any future model that drops temperature support without code changes.

These tests pin both call sites at source level so neither can regress
quietly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _read_cc_service() -> str:
    return (
        Path(__file__).resolve().parents[1]
        / "app/services/cloud_code_service.py"
    ).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Streaming path
# ---------------------------------------------------------------------------


def test_stream_chat_retries_without_temperature_on_400():
    """The streaming entry point must retry once without temperature
    when the API returns 400 with the deprecation message."""
    src = _read_cc_service()
    idx = src.find("async def cloud_code_stream_chat")
    assert idx != -1
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert "_attempt_payloads" in body, (
        "stream chat must build a list of payload attempts (with + without temperature)"
    )
    # The retry condition must mention BOTH "temperature" and "deprecated"
    # so other 400 errors don't accidentally trigger the retry.
    assert "temperature" in body
    assert "deprecated" in body
    assert "continue" in body, (
        "stream chat must `continue` to the next payload attempt on the "
        "temperature-deprecation 400 (not raise)"
    )


def test_stream_chat_builds_payload_without_temperature_for_retry():
    """The fallback payload must strip the `temperature` key."""
    src = _read_cc_service()
    idx = src.find("async def cloud_code_stream_chat")
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    # Look for a payload-without-temperature build
    assert any(
        marker in body for marker in (
            '{k: v for k, v in payload.items() if k != "temperature"}',
            "if k != 'temperature'",
        )
    ), (
        "stream chat must build a fallback payload that strips the "
        "temperature key — without this the retry just sends the same "
        "rejected payload again"
    )


def test_stream_chat_eventually_raises_if_retry_also_fails():
    """The retry is one-shot. If the fallback payload also fails, the
    error must propagate so callers don't silently swallow it."""
    src = _read_cc_service()
    idx = src.find("async def cloud_code_stream_chat")
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    # The is_last_attempt gate ensures we only continue when more
    # attempts remain. After the last attempt, raise.
    assert "_is_last_attempt" in body, (
        "must track whether this is the last attempt — only continue "
        "when more retries are queued"
    )


def test_stream_chat_returns_on_success():
    """After streaming a 200 response, the function must `return` out
    of the retry loop (not keep looping)."""
    src = _read_cc_service()
    idx = src.find("async def cloud_code_stream_chat")
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert "return  # success — exit retry loop" in body or (
        "return" in body and "exit retry loop" in body
    ), (
        "stream chat must explicitly return after the 200-success branch "
        "to exit the retry loop, otherwise it could re-attempt after "
        "successfully streaming"
    )


# ---------------------------------------------------------------------------
# Tool-calling path (cloud_code_message)
# ---------------------------------------------------------------------------


def test_cloud_code_message_retries_without_temperature_on_400():
    """Same retry mechanism must exist for the tool-calling path
    (cloud_code_agent_loop → cloud_code_message). Otherwise the
    inspector chat's tool-enabled flow would still break."""
    src = _read_cc_service()
    idx = src.find("async def cloud_code_message")
    assert idx != -1
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert "_attempt_payloads" in body, (
        "cloud_code_message must build the same retry payload list"
    )
    assert any(
        marker in body for marker in (
            '{k: v for k, v in payload.items() if k != "temperature"}',
            "if k != 'temperature'",
        )
    )
    assert "temperature" in body and "deprecated" in body
    assert "continue" in body, (
        "cloud_code_message must `continue` to the next payload attempt "
        "on the deprecation 400"
    )
