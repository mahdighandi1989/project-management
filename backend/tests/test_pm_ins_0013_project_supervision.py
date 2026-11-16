"""PM-INS-0013 — per-project supervision (read-only) + the all-projects event feed."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.project_supervision as PS
from app.api.routes import project_supervision as R


def test_frontmatter_and_repo_validation():
    fm = PS.parse_frontmatter("---\nname: x\nversion: 3\nupdated: 2026-10-08\nmodelled_on:\n  - a\n---\n# body")
    assert fm == {"name": "x", "version": "3", "updated": "2026-10-08"}
    assert PS.parse_frontmatter("no front matter") == {}
    assert PS.valid_repo("o/Detective-1") and not PS.valid_repo("o/../x") and not PS.valid_repo("bad")


def test_watched_repos_include_self_once(monkeypatch):
    import app.services.oversight_service as OS
    watched = [SimpleNamespace(repo_full_name="o/a"), SimpleNamespace(repo_full_name="o/a"),
               SimpleNamespace(repo_full_name="mahdighandi1989/project-management"), SimpleNamespace(repo_full_name="")]
    monkeypatch.setattr(OS, "get_oversight_service", lambda: SimpleNamespace(watched=watched))
    assert PS.watched_repos() == ["o/a", "mahdighandi1989/project-management"]


def test_summarize_board_shapes_open_urgent_answered():
    board = {"counts": {"open": 1, "answered": 1}, "urgent_waiting": 1, "reports": [
        {"number": 1, "ref": "X-INS-0001", "status": "open", "title": "a", "urgent": True, "notes": []},
        {"number": 2, "ref": "X-INS-0002", "status": "answered", "title": "", "urgent": False,
         "glow": {"tone": "fixed"}, "notes": [{"text": "first note", "at": "t"}]},
    ]}
    s = PS.summarize_board(board, {"urgent": {"next_round": {"at": "soon"}, "cron_utc": "11 */3 * * *"}})
    assert [i["number"] for i in s["open"]] == [1] and [i["number"] for i in s["urgent"]] == [1]
    assert s["answered"][0]["title"] == "first note" and s["answered"][0]["outcome"] == "fixed"
    assert s["next_round"] == {"at": "soon"} and s["crons"]["urgent"] == "11 */3 * * *"


def test_sibling_board_without_config_says_so(monkeypatch):
    monkeypatch.delenv("PROJECT_SUPERVISION_SOURCES", raising=False)
    out = PS.remote_board("o/Detective-1")
    assert out["configured"] is False and "PROJECT_SUPERVISION_SOURCES" in out["reason"]
    monkeypatch.setenv("PROJECT_SUPERVISION_SOURCES", '{"o/x": {"base": "http://insecure"}}')
    assert PS.remote_board("o/x")["configured"] is False  # only https


def test_feed_merges_repos_newest_first_and_counts_file_changes(monkeypatch):
    monkeypatch.setattr(PS, "watched_repos", lambda: ["o/a", "o/b"])
    data = {"o/a": [{"repo": "o/a", "date": "2026-11-01", "files": [{"status": "added"}, {"status": "removed"}]}],
            "o/b": [{"repo": "o/b", "date": "2026-11-02", "files": [{"status": "modified"}]}]}
    monkeypatch.setattr(PS, "_repo_events", lambda r, p, d: data[r])
    out = PS.event_feed()
    assert [e["repo"] for e in out["events"]] == ["o/b", "o/a"]
    assert out["file_counts"] == {"added": 1, "modified": 1, "removed": 1, "renamed": 0}


def test_routes_reject_bad_repo_and_read_self_from_db(monkeypatch, tmp_path):
    with pytest.raises(HTTPException):
        R.board(repo="../etc", db=None)
    with pytest.raises(HTTPException):
        R.feed(limit=10, per_repo=5, detail=0, repo="not a repo")
    import app.api.routes.inspection as I
    monkeypatch.setattr(I, "list_reports", lambda **k: {"counts": {"open": 2}, "reports": [], "urgent_waiting": 0})
    monkeypatch.setattr(I, "schedule", lambda db: {"urgent": {"next_round": None}})
    out = R.board(repo="mahdighandi1989/project-management", db=None)
    assert out["self"] is True and out["live"]["source"] == "db" and out["live"]["counts"] == {"open": 2}
    assert out["git"]["source"] == "offline"  # tests never call GitHub
