"""Tests for the extraction-endpoints performance fix.

🚨 The user reported a backend OOM crash on Render: the oversight
dashboard renders <ExtractedFilesPanel> per task, and each panel was
calling `/api/oversight/tasks/{id}/extractions` on mount. With ~684
tasks the backend received hundreds of serial requests, each returning
1-10 MB of `full_text_cache`, and finally restarted (`Instance
restarted at 10:13:29` in the Render logs).

The fix has two parts which this file pins down:

1. A bulk endpoint `/extractions/counts-by-task` returns a single
   `{task_id: count}` dict, letting the frontend skip mounting the
   panel for tasks with 0 attachments and avoid the 684× fetch
   storm.
2. The per-task `/tasks/{id}/extractions` response excludes the heavy
   `full_text_cache` field by default. Callers that need the text
   call `/extractions/{id}/full-text` (which already streams a single
   extraction) or pass `include_full_text=true`.

If either guarantee regresses, the crash will return.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Helpers — build an isolated ExtractionRepo without touching the singleton.
# ---------------------------------------------------------------------------


def _fresh_repo(tmp_path, monkeypatch):
    """Point the EXTRACTIONS_FILE at a tmp path and return a fresh repo
    so each test starts from an empty state and never mutates the
    shared on-disk store."""
    from app.services import oversight_extraction as oe

    monkeypatch.setattr(oe, "EXTRACTIONS_FILE", tmp_path / "extractions.json")
    monkeypatch.setattr(oe, "_repo_instance", None)
    return oe.get_extraction_repo()


def _seed(repo, task_id: str, *, file_order: int = 0, full_text: str = "X" * 200) -> str:
    """Create a FileExtraction synchronously (asyncio.run on the
    repo's async helper) and return its id."""
    from app.services.oversight_extraction import FileExtraction
    import uuid

    fe = FileExtraction(
        id=str(uuid.uuid4()),
        task_id=task_id,
        session_id="sess-1",
        file_order=file_order,
        original_filename=f"file_{file_order}.pdf",
        mime_type="application/pdf",
        full_text_cache=full_text,
    )
    asyncio.run(repo.create_extraction(fe))
    return fe.id


# ---------------------------------------------------------------------------
# Bulk counts endpoint — one call replaces 684 per-task calls.
# ---------------------------------------------------------------------------


def test_counts_by_task_returns_dict_of_task_id_to_count(tmp_path, monkeypatch):
    repo = _fresh_repo(tmp_path, monkeypatch)
    _seed(repo, "task-A", file_order=0)
    _seed(repo, "task-A", file_order=1)
    _seed(repo, "task-B", file_order=0)

    from app.api.routes.oversight import extractions_counts_by_task

    result = asyncio.run(extractions_counts_by_task())
    assert "counts" in result
    assert result["counts"] == {"task-A": 2, "task-B": 1}


def test_counts_by_task_skips_orphan_extractions(tmp_path, monkeypatch):
    """Extractions with task_id=None (inspector-session uploads not yet
    associated to a task) must NOT appear in the counts dict."""
    repo = _fresh_repo(tmp_path, monkeypatch)
    from app.services.oversight_extraction import FileExtraction
    import uuid

    orphan = FileExtraction(
        id=str(uuid.uuid4()),
        task_id=None,
        session_id="sess-1",
        file_order=0,
        original_filename="orphan.pdf",
        mime_type="application/pdf",
    )
    asyncio.run(repo.create_extraction(orphan))
    _seed(repo, "task-C", file_order=0)

    from app.api.routes.oversight import extractions_counts_by_task

    result = asyncio.run(extractions_counts_by_task())
    assert result["counts"] == {"task-C": 1}


def test_counts_by_task_returns_empty_dict_when_no_extractions(tmp_path, monkeypatch):
    _fresh_repo(tmp_path, monkeypatch)
    from app.api.routes.oversight import extractions_counts_by_task

    result = asyncio.run(extractions_counts_by_task())
    assert result == {"counts": {}}


# ---------------------------------------------------------------------------
# Slim per-task response — the crash multiplier was the full_text_cache.
# ---------------------------------------------------------------------------


def test_task_extractions_default_response_excludes_full_text_cache(tmp_path, monkeypatch):
    """🚨 Regression guard. Each extraction's full_text_cache can be
    multi-MB (entire PDF/video transcript). With 684 tasks × per-task
    fetch × 5-10 MB payload the backend OOM'd. The default response
    MUST omit this field."""
    repo = _fresh_repo(tmp_path, monkeypatch)
    _seed(repo, "task-Z", file_order=0, full_text="X" * 50_000)

    from app.api.routes.oversight import task_extractions

    result = asyncio.run(task_extractions("task-Z"))
    assert result["task_id"] == "task-Z"
    assert result["count"] == 1
    assert len(result["extractions"]) == 1
    extraction = result["extractions"][0]
    # The lightweight metadata MUST be there (so the panel can render
    # the file row), but the heavy text MUST be absent.
    assert "original_filename" in extraction
    assert "mime_type" in extraction
    assert "total_segments" in extraction
    assert "full_text_cache" not in extraction, (
        "full_text_cache MUST be omitted by default — including it "
        "caused the 10 MB payload that crashed the backend"
    )


def test_task_extractions_with_include_flag_returns_full_text(tmp_path, monkeypatch):
    """The flag exists for callers that genuinely need the text in one
    response (e.g. a maintenance script). It must be opt-in only."""
    repo = _fresh_repo(tmp_path, monkeypatch)
    _seed(repo, "task-Y", file_order=0, full_text="HELLO_FULL_TEXT")

    from app.api.routes.oversight import task_extractions

    result = asyncio.run(task_extractions("task-Y", include_full_text=True))
    assert "full_text_cache" in result["extractions"][0]
    assert result["extractions"][0]["full_text_cache"] == "HELLO_FULL_TEXT"


def test_task_extractions_for_task_with_no_files(tmp_path, monkeypatch):
    """Tasks with no attachments still return a valid (empty) shape so
    legacy callers without the counts endpoint don't crash."""
    _fresh_repo(tmp_path, monkeypatch)
    from app.api.routes.oversight import task_extractions

    result = asyncio.run(task_extractions("task-with-nothing"))
    assert result["task_id"] == "task-with-nothing"
    assert result["count"] == 0
    assert result["extractions"] == []
