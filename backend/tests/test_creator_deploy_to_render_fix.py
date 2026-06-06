"""🐛 Creator deploy-to-render: fix wrong repo + wrong root_dir.

User report (verbatim, Persian):
  > یه پروژه رو تو موتور خالق ساختم و پوش کردم به گیت هاب
  > بعد هم اون دکمه سبز رندر رو زدم ولی خطا اومد
  > Root directory 'ai-workspace/projects/proj_fa454439/generated'
  > does not exist

Symptom (from screenshots):
  - User pushed project to NEW standalone repo: mahdighandi1989/Detective-1
    (project at root: backend/, frontend/, docker-compose.yml)
  - Clicked "Deploy to Render" button
  - Render dashboard showed the deploy was configured against the WRONG
    repo: mahdighandi1989/ai-workspace-data with Root Directory
    `ai-workspace/projects/proj_fa454439/generated`
  - That path doesn't exist in ai-workspace-data → deploy fails

Two bugs in `deploy_project` (simple_projects.py):

  1. URL sourcing: only checked `request.github_repo_url` or the
     internal `github_storage` (which always points to the data repo
     ai-workspace-data, NOT the user's pushed project repo). When the
     user runs push_to_github → standalone repo is created, but the
     resulting owner/repo/url were thrown away — never persisted on
     the Project object.

  2. root_dir hardcoded to `ai-workspace/projects/<id>/generated`.
     That path is only valid when deploying from the internal data
     repo. For a standalone pushed repo (Detective-1), the project
     IS the repo root.

Fix:

  a. Added github_owner/github_repo/github_repo_url/github_default_branch
     fields to Project dataclass; populated by push_to_github after
     a successful repo creation + saved via _save_project_meta.

  b. deploy_project now picks source in priority order:
       - request override
       - project.github_repo_url (the standalone repo from push)
       - internal data repo (final fallback)
     and sets root_dir to "" (empty → not sent to Render → root of
     repo) for the first two cases. Only the internal-storage fallback
     uses the subpath form.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Project dataclass — repo metadata fields
# ---------------------------------------------------------------------------


def test_project_dataclass_has_github_repo_fields():
    """Project must carry the standalone-repo metadata, otherwise the
    deploy endpoint can't know which repo the user actually pushed to."""
    from app.services.simple_creator import Project

    p = Project(
        id="proj_x", name="X", description="", project_type="fullstack",
    )
    # All four fields default to None (not-pushed-yet state)
    assert p.github_owner is None
    assert p.github_repo is None
    assert p.github_repo_url is None
    assert p.github_default_branch is None

    # And they're settable
    p.github_owner = "mahdighandi1989"
    p.github_repo = "Detective-1"
    p.github_repo_url = "https://github.com/mahdighandi1989/Detective-1"
    p.github_default_branch = "main"
    assert p.github_repo_url == "https://github.com/mahdighandi1989/Detective-1"


def test_project_to_dict_includes_github_fields():
    """to_dict() is what gets persisted to project.json — must include
    the repo fields, otherwise they vanish on the next load."""
    from app.services.simple_creator import Project

    p = Project(
        id="proj_x", name="X", description="", project_type="fullstack",
        github_owner="mahdighandi1989", github_repo="Detective-1",
        github_repo_url="https://github.com/mahdighandi1989/Detective-1",
        github_default_branch="main",
    )
    d = p.to_dict()
    assert d["github_owner"] == "mahdighandi1989"
    assert d["github_repo"] == "Detective-1"
    assert d["github_repo_url"] == "https://github.com/mahdighandi1989/Detective-1"
    assert d["github_default_branch"] == "main"


def test_load_existing_projects_restores_github_fields(tmp_path, monkeypatch):
    """After a backend restart, the github_repo fields must be reloaded
    from project.json so the deploy endpoint still finds the standalone
    repo info."""
    import json
    import importlib

    # Build a fake workspace with one project.json containing repo fields
    workspace = tmp_path / "workspace"
    proj_dir = workspace / "proj_test1"
    proj_dir.mkdir(parents=True)
    meta = {
        "id": "proj_test1",
        "name": "Detective-1",
        "description": "OSINT",
        "project_type": "fullstack",
        "status": "created",
        "created_at": "2026-06-06T12:00:00",
        "files": [],
        "structure": {},
        "technologies": [],
        "github_owner": "mahdighandi1989",
        "github_repo": "Detective-1",
        "github_repo_url": "https://github.com/mahdighandi1989/Detective-1",
        "github_default_branch": "main",
    }
    (proj_dir / "project.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8",
    )

    from app.services.simple_creator import SimpleProjectCreator

    creator = SimpleProjectCreator.__new__(SimpleProjectCreator)
    creator.workspace = workspace
    creator.projects = {}
    creator._load_existing_projects()

    p = creator.projects["proj_test1"]
    assert p.github_owner == "mahdighandi1989"
    assert p.github_repo == "Detective-1"
    assert p.github_repo_url == "https://github.com/mahdighandi1989/Detective-1"
    assert p.github_default_branch == "main"


def test_load_existing_projects_handles_missing_github_fields(tmp_path):
    """Old project.json files (pre-fix) don't have the repo fields. The
    loader must default them to None instead of crashing."""
    import json

    workspace = tmp_path / "workspace"
    proj_dir = workspace / "proj_old"
    proj_dir.mkdir(parents=True)
    meta = {
        "id": "proj_old", "name": "Old", "description": "",
        "project_type": "fastapi", "status": "created",
        "created_at": "2026-01-01T00:00:00",
        "files": [], "structure": {}, "technologies": [],
        # NO github_* fields — simulating pre-fix data
    }
    (proj_dir / "project.json").write_text(json.dumps(meta), encoding="utf-8")

    from app.services.simple_creator import SimpleProjectCreator

    creator = SimpleProjectCreator.__new__(SimpleProjectCreator)
    creator.workspace = workspace
    creator.projects = {}
    creator._load_existing_projects()

    p = creator.projects["proj_old"]
    assert p.github_owner is None
    assert p.github_repo_url is None


# ---------------------------------------------------------------------------
# deploy_project — source-priority + root_dir logic
# ---------------------------------------------------------------------------


def _slice_deploy_project_body() -> str:
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project")
    assert idx != -1
    rest = src[idx + 1:]
    # Slice to next top-level function/class
    nxt = rest.find("\n@router.")
    if nxt == -1:
        nxt = rest.find("\nclass ")
    body = rest if nxt == -1 else rest[:nxt]
    return body


def test_deploy_project_reads_repo_from_project_dataclass():
    """The endpoint must read github_repo_url from the Project object
    BEFORE falling back to the internal data repo. Otherwise users who
    just pushed to a standalone repo (Detective-1) would have Render
    misconfigured to the data repo."""
    body = _slice_deploy_project_body()
    assert "project.github_repo_url" in body, (
        "deploy_project must consult project.github_repo_url — that's "
        "where push_to_github persisted the standalone repo URL"
    )


def test_deploy_project_uses_empty_root_dir_for_standalone_repo():
    """For a standalone repo (Detective-1), the project files are at the
    REPO ROOT. root_dir must be "" (or unset) so Render reads from the
    root, not from a non-existent subpath."""
    body = _slice_deploy_project_body()
    # Pin that root_dir is initialized to "" and only the internal-storage
    # fallback sets it to the subpath form.
    assert 'root_dir = ""' in body, (
        "root_dir must default to empty so standalone-repo deploys read "
        "from the repo root"
    )
    # The subpath form must ONLY appear in the internal_storage branch
    subpath_marker = 'f"ai-workspace/projects/{project_id}/generated"'
    assert subpath_marker in body, (
        "subpath fallback for internal storage must still be present"
    )


def test_deploy_project_priority_order_request_then_project_then_storage():
    """Priority is (1) request override → (2) project.github_repo_url →
    (3) internal github_storage. Pin the order."""
    body = _slice_deploy_project_body()
    req_idx = body.find("request.github_repo_url")
    proj_idx = body.find("project.github_repo_url")
    storage_idx = body.find("github_storage = get_github_storage()")
    assert req_idx != -1 and proj_idx != -1 and storage_idx != -1
    assert req_idx < proj_idx < storage_idx, (
        "deploy_project source priority must be: request → project → storage"
    )


def test_deploy_project_uses_project_branch_when_set():
    """When the project has its own default_branch persisted (e.g., 'main'
    from a freshly-created repo), deploy_project must use that — otherwise
    Render might try to clone a non-existent branch."""
    body = _slice_deploy_project_body()
    assert "project.github_default_branch" in body, (
        "deploy_project must honor project.github_default_branch when set"
    )


def test_deploy_project_instructions_mention_push_button():
    """When the project hasn't been pushed yet, the error message should
    direct the user to the «GitHub به push» button (which is what the
    UI shows), not the old generic instructions."""
    body = _slice_deploy_project_body()
    assert "GitHub به push" in body, (
        "no-repo error must point user to the actual «GitHub به push» "
        "button in the UI"
    )


# ---------------------------------------------------------------------------
# push_to_github — persistence
# ---------------------------------------------------------------------------


def _slice_push_to_github_body() -> str:
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def push_to_github")
    assert idx != -1
    rest = src[idx + 1:]
    nxt = rest.find("\n@router.")
    body = rest if nxt == -1 else rest[:nxt]
    return body


def test_push_to_github_persists_repo_info_on_project():
    """After successful repo creation, push_to_github must store the
    repo metadata on the Project so deploy_project can find it later."""
    body = _slice_push_to_github_body()
    assert "project.github_owner = owner" in body
    assert "project.github_repo = desired_repo" in body
    assert "project.github_repo_url = repo_html_url" in body
    assert "project.github_default_branch = default_branch" in body
    assert "creator._save_project_meta(project)" in body, (
        "must call _save_project_meta to persist the new fields to disk"
    )


def test_push_to_github_persists_before_auto_register_block():
    """Persistence must happen even if `len(failed) > 0` — the repo was
    created, some files may have failed. We still want deploy to find the
    repo. Pin that the save happens BEFORE the `if len(failed) == 0:`
    block that gates the watched-registration."""
    body = _slice_push_to_github_body()
    save_idx = body.find("creator._save_project_meta(project)")
    failed_zero_idx = body.find("if len(failed) == 0:")
    assert save_idx != -1 and failed_zero_idx != -1
    assert save_idx < failed_zero_idx, (
        "github_* fields must be saved unconditionally on repo creation, "
        "not only on full success — even partial pushes leave a valid repo"
    )
