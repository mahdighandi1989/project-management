# -*- coding: utf-8 -*-
"""(PM-INS-0010) «جزوه و دفتر کار» opens the handbook / work log of every watched repo (`?repo=owner/name`)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIB = "mahdighandi1989/Detective-1"

TREE = {
    "": [{"name": "README.md", "path": "README.md", "type": "file"},
         {"name": "docs", "path": "docs", "type": "dir"},
         {"name": "app.py", "path": "app.py", "type": "file"}],
    "docs": [{"name": "WORKLOG.md", "path": "docs/WORKLOG.md", "type": "file"},
             {"name": "HANDBOOK", "path": "docs/HANDBOOK", "type": "dir"},
             {"name": "supervisor", "path": "docs/supervisor", "type": "dir"}],
    "docs/HANDBOOK": [{"name": "HANDBOOK.md", "path": "docs/HANDBOOK/HANDBOOK.md", "type": "file"},
                      {"name": "PROGRESS.md", "path": "docs/HANDBOOK/PROGRESS.md", "type": "file"}],
    "docs/supervisor": [{"name": "PROMPT.md", "path": "docs/supervisor/PROMPT.md", "type": "file"}],
}
FILES = {
    "README.md": "# Detective\n",
    "docs/WORKLOG.md": "# دفتر کار دتکتیو\n\n## 2026-11-15 — کار\nمتنِ ویژهٔ دتکتیو\n",
    "docs/HANDBOOK/HANDBOOK.md": "# جزوهٔ دتکتیو\n\n## بخش\n",
    "docs/HANDBOOK/PROGRESS.md": "# دفتر پیشرفت\n",
    "docs/supervisor/PROMPT.md": "# ناظر\n",
}


def _client(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import handbook
    from app.services import project_supervision as ps
    from app.services import repo_docs

    monkeypatch.setattr(ps, "watched_repos", lambda: [SIB, repo_docs.repo()])
    real_list, real_read = repo_docs.list_dir, repo_docs.read_text

    def fake_list(path, repo_name=None):
        if repo_name and repo_name.lower() == SIB.lower():
            return TREE.get(path.strip("/"), [])
        return real_list(path, repo_name)

    def fake_read(path, repo_name=None):
        if repo_name and repo_name.lower() == SIB.lower():
            if path in FILES:
                return FILES[path], "github"
            raise FileNotFoundError(path)
        return real_read(path, repo_name)

    monkeypatch.setattr(repo_docs, "list_dir", fake_list)
    monkeypatch.setattr(repo_docs, "read_text", fake_read)
    monkeypatch.setattr(repo_docs, "commits_page", lambda page=1, per_page=100, repo_name=None: (
        [{"sha": "d1d1d1d", "date": "2026-11-15T10:00:00Z", "message": "feat: detective", "author": "x", "url": ""}]
        if repo_name else []))
    app = FastAPI()
    app.include_router(handbook.router, prefix="/api")
    return TestClient(app)


def test_repos_lists_this_project_first_then_watched(monkeypatch):
    d = _client(monkeypatch).get("/api/handbook/repos").json()
    assert d["repos"][0]["self"] is True
    assert any(r["repo"] == SIB and not r["self"] for r in d["repos"])


def test_sibling_catalogue_discovers_handbook_worklog_and_changelog(monkeypatch):
    c = _client(monkeypatch)
    docs = c.get(f"/api/handbook/docs?repo={SIB}").json()
    by = {d["slug"]: d for d in docs}
    assert {"HANDBOOK", "PROGRESS", "WORKLOG", "CHANGELOG", "root-README", "supervisor-PROMPT"} <= set(by)
    assert "ACTIVITY" not in by  # this app's own model activity is not per repo
    assert by["HANDBOOK"]["path"] == "docs/HANDBOOK/HANDBOOK.md" and by["HANDBOOK"]["group"] == "جزوه"
    assert by["WORKLOG"]["group"] == "دفتر کار"
    assert by["HANDBOOK"]["github_url"].startswith(f"https://github.com/{SIB}/blob/")
    assert all(d["repo"] == SIB for d in docs)

    w = c.get(f"/api/handbook/doc/WORKLOG?repo={SIB}").json()
    assert "متنِ ویژهٔ دتکتیو" in w["content"] and w["repo"] == SIB
    ch = c.get(f"/api/handbook/doc/CHANGELOG?repo={SIB}").json()
    assert "d1d1d1d" in ch["content"] and SIB in ch["content"]
    hits = c.get(f"/api/handbook/search?q=ویژهٔ دتکتیو&repo={SIB}").json()["hits"]
    assert hits and hits[0]["slug"] == "WORKLOG"
    exp = c.get(f"/api/handbook/export?repo={SIB}")
    assert exp.status_code == 200 and "جزوهٔ دتکتیو" in exp.text and "Detective-1-all" in exp.headers["content-disposition"]


def test_repo_param_is_limited_to_watched_repos(monkeypatch):
    c = _client(monkeypatch)
    assert c.get("/api/handbook/docs?repo=someone/else").status_code == 404
    assert c.get("/api/handbook/docs?repo=bad name").status_code == 400
    # this project itself, by name, is the default reader (HANDBOOK + ACTIVITY present)
    from app.services import repo_docs

    slugs = [d["slug"] for d in c.get(f"/api/handbook/docs?repo={repo_docs.repo()}").json()]
    assert "HANDBOOK" in slugs and "ACTIVITY" in slugs


def test_foreign_read_never_falls_back_to_local_checkout():
    from app.services import repo_docs

    # offline (pytest): another repo's file must NOT be served from this checkout's identical path
    try:
        repo_docs.read_text("docs/WORKLOG.md", SIB)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("foreign repo fell back to local file")
    assert repo_docs.list_dir("docs", SIB) == []
    assert repo_docs.read_text("docs/WORKLOG.md")[1] == "local"
