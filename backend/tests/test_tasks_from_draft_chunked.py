"""🐛 (Render edge body-cap) — POST /api/oversight/tasks fail با ERR_FAILED
وقتی payload بزرگ است (prompt + task_steps چند صد KB).

از screenshot کاربر:
  - browser console: net::ERR_FAILED روی /api/oversight/tasks
  - backend logs: هیچ POST log برای /tasks (فقط OPTIONS preflight)
  → Render edge قبل از رسیدن به backend body را reject می‌کند.

راه‌حل: همان pattern موجود idea-draft را برای ساخت تسک هم استفاده کنیم —
frontend اگر body > 500KB، JSON کامل را chunked به /idea-draft/* آپلود
می‌کند و سپس /tasks/from-draft را با draft_id کوچک صدا می‌زند.

این فایل source-level pin های این fix را دارد.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_tasks_from_draft_endpoint_exists():
    """POST /tasks/from-draft must exist with payload_draft_id parameter."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/oversight.py"
    ).read_text(encoding="utf-8")
    assert '@router.post("/tasks/from-draft")' in src, (
        "must expose /tasks/from-draft endpoint so frontend can use the "
        "chunked draft pattern for large payloads"
    )
    idx = src.find('async def create_task_from_draft')
    assert idx != -1
    body = src[idx:idx + 3000]
    # Must accept payload_draft_id (query param or arg)
    assert "payload_draft_id" in body
    # Must consume the draft (one-shot read)
    assert "_consume_idea_draft" in body, (
        "the new endpoint must consume the draft so memory is freed"
    )
    # Must parse JSON and validate with TaskCreate
    assert "TaskCreate(" in body, (
        "must validate the draft JSON with the existing TaskCreate schema"
    )
    # Must surface validation errors with a useful message
    assert "draft_payload_validation_failed" in body
    assert "draft_json_parse_error" in body


def test_tasks_from_draft_returns_404_when_draft_missing():
    """If the draft was already consumed or never existed, return 404 with
    a clear code so the frontend can re-upload rather than silently fail."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/oversight.py"
    ).read_text(encoding="utf-8")
    idx = src.find('async def create_task_from_draft')
    assert idx != -1
    body = src[idx:idx + 3000]
    assert "task_payload_draft_not_found_or_expired" in body, (
        "must return a distinctive error code so frontend retries cleanly"
    )


def test_frontend_uses_chunked_upload_above_threshold():
    """Source pin: oversight/page.tsx savePromptAsTask must check the
    JSON byte size and switch to the chunked /idea-draft + from-draft
    path when above the LARGE_THRESHOLD.

    🐛 (regression guard) — Threshold must stay at 50KB (= 50 * 1024).
    کاربر روی Lifemanager با 500KB ای که قبلاً ست شده بود همچنان «network
    — Failed to fetch» می‌دید چون payload ~100-200KB بود ولی Render edge
    قبل از 500KB body را reject می‌کرد. مرز ایمن همان 50KB است که
    /idea-draft هم استفاده می‌کند. اگر کسی این عدد را بالا برد، bug
    دوباره برمی‌گردد.
    """
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/oversight/page.tsx"
    ).read_text(encoding="utf-8")
    # Threshold + size measurement
    assert "LARGE_THRESHOLD" in src, (
        "must define a threshold for switching to chunked upload"
    )
    assert "LARGE_THRESHOLD = 50 * 1024" in src, (
        "threshold must stay at 50KB — higher values let payloads through "
        "that Render edge silently rejects (Failed to fetch with no logs)"
    )
    assert "new TextEncoder().encode(payloadJson)" in src, (
        "must measure UTF-8 byte size of the JSON payload (not just .length "
        "which is char count and undercounts Persian/Arabic by ~2x)"
    )
    # Routes the chunked path uses
    assert "/api/oversight/idea-draft/start" in src
    assert "/api/oversight/idea-draft/" in src and "/chunk" in src
    assert "/api/oversight/tasks/from-draft?payload_draft_id=" in src


def test_frontend_chunk_size_respects_utf8_bytes():
    """The chunk-size loop must convert chars-to-bytes correctly so a
    chunk of Persian text (~2 bytes/char) doesn't exceed the per-chunk
    byte cap. Pin the byte-aware slicing logic."""
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/oversight/page.tsx"
    ).read_text(encoding="utf-8")
    # The byte-aware loop appears in the idea-draft chunked upload AND
    # the new task-payload chunked upload. We pin that the savePromptAsTask
    # function specifically contains the byte-cap shrinking loop.
    save_idx = src.find("savePromptAsTask = async")
    assert save_idx != -1
    # Look for the byte cap shrinking pattern within ~6000 chars of the function
    body = src[save_idx:save_idx + 10000]
    assert "encoded.length > byteCap" in body, (
        "savePromptAsTask must shrink the chunk until UTF-8 bytes fit "
        "under the cap — otherwise large Persian payloads still 413"
    )


def test_frontend_small_payload_still_uses_direct_post():
    """The chunked path adds an extra roundtrip; for normal-sized tasks
    we should keep the single direct POST. Pin the else-branch."""
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/oversight/page.tsx"
    ).read_text(encoding="utf-8")
    save_idx = src.find("savePromptAsTask = async")
    assert save_idx != -1
    body = src[save_idx:save_idx + 10000]
    # Direct POST path must still exist after the chunked branch
    assert "`${API_BASE}/api/oversight/tasks`" in body, (
        "small payloads must still use the direct POST /tasks endpoint, "
        "not the chunked path (which would add latency for no reason)"
    )
