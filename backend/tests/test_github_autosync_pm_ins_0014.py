"""PM-INS-0014 — سینکِ خودکارِ پروژه‌های GitHub.

۱) بی‌کلیک: کامیتِ تازه ⇒ سینک؛ بی‌کامیت ⇒ فقط بررسیِ سبک.
۲) برچسبِ خصوصی از خودِ GitHub می‌آید و تنظیماتِ ثبت‌شده در extra_data پاک نمی‌شوند.
۳) سقفِ ثابتِ ۱۰۰ فایل نیست؛ هر ردشده با دلیل شمرده می‌شود («N از M»).
۴) افزایشی (فایلِ بی‌تغییر دوباره دانلود نمی‌شود) و حذف در GitHub ⇒ حذف + ثبت در تاریخچه.
"""
import asyncio
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class FakeGitHub:
    def __init__(self):
        self.private = True
        self.head = "c1"
        self.files = {f"src/pages/p{i}.jsx": f"v1-{i}" for i in range(150)}
        self.files["README.md"] = "hi"
        self.files["public/logo.png"] = "bin"
        self.downloads = []

    def tree(self):
        return [{"type": "blob", "path": p, "size": len(c), "sha": f"{self.head}:{c}"}
                for p, c in self.files.items()] + [{"type": "tree", "path": "src"}]


@pytest.fixture
def env(tmp_path, monkeypatch):
    from app.core import database
    from app.core.database import Base
    from app.models import project as _p  # noqa: F401
    from app.services import github_import as gi

    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["projects"], Base.metadata.tables["project_files"]])
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "SessionLocal", Session)

    gh = FakeGitHub()
    svc = gi.GitHubImportService()
    svc.request_delay = 0

    async def access(owner, repo, token=None):
        return {"success": True, "private": gh.private, "repo_info": {
            "name": repo, "html_url": f"https://github.com/{owner}/{repo}", "default_branch": "main",
            "private": gh.private}}

    async def head(owner, repo, branch, token=None):
        return gh.head

    async def tree(owner, repo, branch=None, token=None):
        return {"success": True, "sha": "t", "truncated": False, "tree": gh.tree()}

    async def langs(owner, repo, token=None):
        return {"JavaScript": 1}

    async def content(owner, repo, path, branch=None, token=None):
        gh.downloads.append(path)
        return {"success": True, "content": gh.files[path], "size": len(gh.files[path])}

    svc.check_repo_access, svc.get_branch_head, svc.get_repo_tree = access, head, tree
    svc.get_repo_languages, svc.get_file_content = langs, content
    monkeypatch.setattr(gi, "_github_import_service", svc)
    return Session, gh


def _run(coro):
    return asyncio.run(coro)


def test_autosync_full_incremental_private_and_deletes(env):
    from app.models.project import Project, ProjectFile
    from app.services.github_autosync import sync_project

    Session, gh = env
    db = Session()
    db.add(Project(id="gh_o_quran", name="quran", project_type="github_import",
                   extra_data=json.dumps({"source": "github", "owner": "o", "repo": "quran", "private": True,
                                          "sync_settings": {"auto_sync_enabled": True}})))
    db.commit(); db.close()

    r = _run(sync_project("gh_o_quran"))
    assert r["success"] and not r["skipped"]
    db = Session()
    n = db.query(ProjectFile).filter_by(project_id="gh_o_quran").count()
    assert n == 151, "no 100-file cap: all 150 pages + README"
    meta = json.loads(db.query(Project).get("gh_o_quran").extra_data)
    db.close()
    assert meta["sync_settings"] == {"auto_sync_enabled": True}, "extra_data merged, not overwritten"
    assert meta["private"] is True
    gs = meta["github_sync"]
    assert gs["last_synced_sha"] == "c1" and gs["stored_files"] == 151 and gs["repo_files"] == 152
    assert gs["report"]["skipped_ext"] == 1  # the .png — explained, not hidden

    # بی‌کامیتِ تازه ⇒ هیچ دانلودی
    gh.downloads.clear()
    r = _run(sync_project("gh_o_quran"))
    assert r["skipped"] and gh.downloads == []

    # کامیتِ تازه: یک تغییر، یک حذف، یک افزودن؛ مخزن عمومی شد
    gh.head = "c2"
    gh.private = False
    old = {p: f"c1:{c}" for p, c in gh.files.items()}
    gh.files["src/pages/p0.jsx"] = "v2-0"
    del gh.files["src/pages/p1.jsx"]
    gh.files["src/lib/new.js"] = "n"
    # sha ِ فایل‌های بی‌تغییر همان sha ِ قبلی بماند
    gh.tree = lambda: [{"type": "blob", "path": p, "size": len(c),
                        "sha": old.get(p) if old.get(p, "").endswith(":" + c) else f"c2:{c}"}
                       for p, c in gh.files.items()]
    gh.downloads.clear()
    r = _run(sync_project("gh_o_quran"))
    assert r["success"] and r["added"] == 1 and r["changed"] == 1 and r["removed"] == 1
    assert sorted(gh.downloads) == ["src/lib/new.js", "src/pages/p0.jsx"], "incremental"
    db = Session()
    paths = {f.file_path for f in db.query(ProjectFile).filter_by(project_id="gh_o_quran")}
    meta = json.loads(db.query(Project).get("gh_o_quran").extra_data)
    db.close()
    assert "src/pages/p1.jsx" not in paths and "src/lib/new.js" in paths
    assert meta["private"] is False  # از خودِ GitHub
    last = meta["github_sync"]["history"][-1]
    assert last["removed"] == ["src/pages/p1.jsx"] and last["commit"] == "c2" and last["trigger"] == "auto"


def test_cap_is_reported_not_silent(env, monkeypatch):
    from app.services.github_import import get_github_import_service

    monkeypatch.setenv("GITHUB_IMPORT_MAX_FILES", "40")
    res = _run(get_github_import_service().import_repository("o/quran"))
    rep = res["sync_report"]
    assert len(res["files"]) == 40 and rep["capped"] == 111 and rep["kept"] == 40
    assert res["files"][0]["path"] == "README.md"  # important files first


def test_list_reports_real_file_count(env):
    """PM-INS-0016 — /api/github/imported returned file_count 0 for every project."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import github_import as R
    from app.core.database import get_db
    from app.models.project import Project, ProjectFile

    Session, _ = env
    db = Session()
    db.add(Project(id="gh_o_a", name="a", project_type="github_import"))
    db.add_all([ProjectFile(project_id="gh_o_a", file_path=f"f{i}") for i in range(3)])
    db.commit(); db.close()
    app = FastAPI(); app.include_router(R.router, prefix="/api")

    def _db():
        d = Session()
        try:
            yield d
        finally:
            d.close()
    app.dependency_overrides[get_db] = _db
    r = TestClient(app).get("/api/github/imported").json()
    assert [p["file_count"] for p in r["projects"]] == [3]
