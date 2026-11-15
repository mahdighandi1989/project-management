# -*- coding: utf-8 -*-
"""/api/handbook/{recent,changes} — the live feeds of the home page and the help circle (2026-11-15)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import handbook

    app = FastAPI()
    app.include_router(handbook.router, prefix="/api")
    return TestClient(app)


def test_recent_reads_the_worklog_newest_first_with_signatures():
    d = _client().get("/api/handbook/recent?limit=3").json()
    assert len(d["worklog"]) == 3
    assert d["worklog"][0]["title"] >= d["worklog"][-1]["title"][:10]  # newest first (dated titles)
    assert any(w["signed"] for w in d["worklog"])


def test_changes_merges_commits_per_file_and_rejects_unsafe_paths(monkeypatch):
    from app.services import repo_docs

    def fake(n, path=None):
        return [{"sha": "aaa", "date": "2026-11-15T01:00:00Z", "message": "m", "author": "x", "url": ""},
                {"sha": path[:3], "date": "2026-11-14T01:00:00Z", "message": path, "author": "x", "url": ""}]

    monkeypatch.setattr(repo_docs, "recent_commits", fake)
    d = _client().get("/api/handbook/changes?files=frontend/a.tsx,backend/b.py,../etc/passwd").json()
    assert d["files"] == ["frontend/a.tsx", "backend/b.py"]
    shared = next(c for c in d["commits"] if c["sha"] == "aaa")
    assert shared["files"] == ["frontend/a.tsx", "backend/b.py"]
    assert d["commits"][0]["sha"] == "aaa"  # newest first
