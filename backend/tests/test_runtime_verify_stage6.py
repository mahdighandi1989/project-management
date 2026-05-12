"""Stage 6 — Evidence storage tests."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from app.services.verify_runtime.storage import (
    ensure_run_dir,
    write_manifest,
    cleanup_old_runs,
    list_runs_for_task,
    resolve_evidence_file,
)


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


class TestEnsureRunDir:
    def test_creates_nested(self, storage):
        p = ensure_run_dir(storage, "task1", "run1")
        assert p.is_dir()
        assert p == storage / "verify_evidence" / "task1" / "run1"

    def test_idempotent(self, storage):
        ensure_run_dir(storage, "t", "r")
        ensure_run_dir(storage, "t", "r")  # should not raise


class TestWriteManifest:
    def test_writes_valid_json(self, storage):
        run_dir = ensure_run_dir(storage, "t", "r1")
        mpath = write_manifest(
            run_dir,
            task_id="t",
            run_id="r1",
            probe_results=[{"ac_id": "a1", "status": "passed"}],
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:05+00:00",
        )
        assert mpath.is_file()
        data = json.loads(mpath.read_text())
        assert data["task_id"] == "t"
        assert data["run_id"] == "r1"
        assert data["probe_count"] == 1


class TestCleanupOldRuns:
    def test_keeps_last_n(self, storage):
        for i in range(7):
            d = ensure_run_dir(storage, "t1", f"run{i}")
            (d / "file.txt").write_text(f"run {i}")
            time.sleep(0.01)  # mtime ordering
        deleted = cleanup_old_runs(storage, "t1", keep=3)
        assert deleted == 4
        # 3 جدیدترین باقی می‌مانند: run6, run5, run4
        runs = list_runs_for_task(storage, "t1")
        assert len(runs) == 3
        names = {r["run_id"] for r in runs}
        assert names == {"run4", "run5", "run6"}

    def test_no_runs_no_error(self, storage):
        assert cleanup_old_runs(storage, "nonexistent_task", keep=5) == 0

    def test_keep_more_than_existing(self, storage):
        for i in range(2):
            ensure_run_dir(storage, "t", f"r{i}")
        deleted = cleanup_old_runs(storage, "t", keep=5)
        assert deleted == 0


class TestListRuns:
    def test_empty_for_unknown_task(self, storage):
        assert list_runs_for_task(storage, "x") == []

    def test_returns_metadata(self, storage):
        run_dir = ensure_run_dir(storage, "t", "r1")
        write_manifest(
            run_dir, task_id="t", run_id="r1",
            probe_results=[{"x": 1}],
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:05+00:00",
        )
        (run_dir / "shot.png").write_bytes(b"x" * 100)
        runs = list_runs_for_task(storage, "t")
        assert len(runs) == 1
        assert runs[0]["run_id"] == "r1"
        assert runs[0]["probe_count"] == 1
        assert runs[0]["size_bytes"] > 100  # manifest + shot


class TestResolveEvidenceFile:
    def test_resolves_real_file(self, storage):
        d = ensure_run_dir(storage, "t", "r")
        (d / "shot.png").write_bytes(b"fake")
        p = resolve_evidence_file(storage, "t", "r", "shot.png")
        assert p is not None
        assert p.is_file()
        assert p.name == "shot.png"

    def test_blocks_traversal(self, storage):
        ensure_run_dir(storage, "t", "r")
        # سعی برای رفتن بالاتر از run_id
        p = resolve_evidence_file(storage, "t", "r", "../../../etc/passwd")
        assert p is None

    def test_blocks_nonexistent(self, storage):
        ensure_run_dir(storage, "t", "r")
        p = resolve_evidence_file(storage, "t", "r", "no_such_file.png")
        assert p is None

    def test_resolves_nested_subdir(self, storage):
        d = ensure_run_dir(storage, "t", "r")
        sub = d / "ac01"
        sub.mkdir()
        (sub / "step1.png").write_bytes(b"x")
        p = resolve_evidence_file(storage, "t", "r", "ac01/step1.png")
        assert p is not None
        assert p.name == "step1.png"
