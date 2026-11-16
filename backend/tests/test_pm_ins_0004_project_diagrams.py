"""PM-INS-0004 — one entry per project in the diagrams picker; saved diagrams per project."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import diagrams as D


def test_repo_full_name_of_a_local_project():
    assert D._local_repo_full_name(SimpleNamespace(github_owner="o", github_repo="Detective-1")) == "o/Detective-1"
    assert D._local_repo_full_name(SimpleNamespace(github_repo_url="https://github.com/o/r.git")) == "o/r"
    assert D._local_repo_full_name(SimpleNamespace()) == ""


def test_watched_repo_linked_to_a_local_project_is_listed_once(monkeypatch):
    import app.services.simple_creator as SC
    import app.services.oversight_service as OS
    local = SimpleNamespace(id="proj_1", name="Detective-1", description="", project_type="fullstack", files=[],
                            github_owner="o", github_repo="Detective-1", github_repo_url=None)
    monkeypatch.setattr(SC, "get_simple_creator", lambda: SimpleNamespace(list_projects=lambda: [local]))
    watched = [SimpleNamespace(id="w1", repo_full_name="o/Detective-1", user_notes="", language="fullstack", repo_url=""),
               SimpleNamespace(id="w2", repo_full_name="o/other", user_notes="", language="py", repo_url="")]
    monkeypatch.setattr(OS, "get_oversight_service", lambda: SimpleNamespace(watched=watched))
    items = asyncio.run(D.list_diagram_projects())["items"]
    assert [(i["source"], i["id"]) for i in items] == [("local", "proj_1"), ("github", "w2")]
    assert items[0]["repo"] == "o/Detective-1"


def test_saved_diagrams_per_project(tmp_path, monkeypatch):
    import app.core.database as DB
    monkeypatch.setattr(DB, "DATABASE_DIR", str(tmp_path))
    req = D.SaveDiagramRequest(source="local", id="proj_1", mermaid="flowchart LR\n A-->B", diagram_type="tree", title="🌲")
    first = asyncio.run(D.save_diagram(req))
    assert first["duplicate"] is False
    assert asyncio.run(D.save_diagram(req))["duplicate"] is True  # same code is not stored twice
    asyncio.run(D.save_diagram(D.SaveDiagramRequest(source="local", id="proj_1", mermaid="classDiagram\n class A")))
    listed = asyncio.run(D.list_saved_diagrams("local", "proj_1"))
    assert listed["count"] == 2 and listed["items"][0]["mermaid"].startswith("classDiagram")  # newest first
    assert asyncio.run(D.list_saved_diagrams("local", "proj_2"))["count"] == 0  # per project
    with pytest.raises(HTTPException):
        asyncio.run(D.list_saved_diagrams("ftp", "x"))
    with pytest.raises(HTTPException):
        asyncio.run(D.save_diagram(D.SaveDiagramRequest(source="local", id="p", mermaid="  ")))
