"""🆕 Creator deploy parity with Inspector's smart deploy.

User report: created Detective-1 (fullstack), pushed to standalone repo,
clicked Deploy → kept failing. After v1/v2 fixed the wrong-repo bug, the
deeper issue surfaced: Creator's deploy only made ONE service (with a
single root_dir). Detective-1 is fullstack — frontend AND backend — and
Inspector's deploy in `/projects/[id]` had been smart about this for a
while (AI reads the repo, decides multi-service, static_site vs
web_service, env vars, etc).

User asked: "ببین میتونی الگو بگیری ازش دقیقا بتونی ایرادات این
قسمت رو برطرف کنی و ارتقا بدی" — i.e. lift Inspector's pattern into
Creator.

Three new pieces:

1. `_ai_analyze_repo_only` — the DB-less core of Inspector's AI
   analyzer. Both Inspector and Creator can call it.

2. `_ai_analyze_project` — kept as an Inspector-side wrapper that
   does the DB-aware model selection (`_smart_select_model`) then
   delegates to the new helper. Backward compatible.

3. Two new Creator endpoints:
     POST /api/simple/projects/{id}/deploy/render-ai
        AI multi-service deploy (analog of Inspector's
        /inspector/create-render-service).
     GET  /api/simple/projects/{id}/deploy/render-prefill
        Returns the Render `dashboard.render.com/select-repo?...` URL
        so the Free-plan button can open it (user does the rest in
        Render UI).

Frontend: new modal in `project/[id]/page.tsx` mirroring Inspector's
deploy modal — Free (redirect) and AI auto (multi-service) buttons.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# _ai_analyze_repo_only — extracted DB-less helper
# ---------------------------------------------------------------------------


def test_ai_analyze_repo_only_exists_and_takes_no_db():
    """The new helper must exist and accept the simple-creator-friendly
    parameter set (no `db`, no `project_id`)."""
    from app.api.routes.render_logs import _ai_analyze_repo_only

    sig = inspect.signature(_ai_analyze_repo_only)
    params = set(sig.parameters)
    # Required positional/keyword params
    assert {"owner", "repo", "branch", "github_token", "github_url"} <= params
    # Must NOT take db or project_id (the whole point of extracting it)
    assert "db" not in params
    assert "project_id" not in params
    # model_id is optional (None → fallback default)
    assert "model_id" in params
    assert sig.parameters["model_id"].default is None


def test_ai_analyze_project_still_exists_for_backward_compat():
    """Inspector calls `_ai_analyze_project` directly. The refactor must
    preserve that signature (db + project_id) — only the implementation
    changed (now delegates to the new helper)."""
    from app.api.routes.render_logs import _ai_analyze_project

    sig = inspect.signature(_ai_analyze_project)
    params = set(sig.parameters)
    assert {"owner", "repo", "branch", "github_token", "github_url",
            "project_id", "db"} <= params


def test_ai_analyze_project_body_now_uses_helper():
    """Source check: the inspector-side function must delegate to
    `_ai_analyze_repo_only` — not duplicate the GitHub-fetch + prompt
    logic. Otherwise a future fix in one would silently miss the other."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/render_logs.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def _ai_analyze_project")
    assert idx != -1
    body = src[idx:idx + 2000]
    assert "_ai_analyze_repo_only" in body, (
        "_ai_analyze_project must delegate to _ai_analyze_repo_only — "
        "otherwise the two implementations will drift"
    )


# ---------------------------------------------------------------------------
# New Creator endpoints
# ---------------------------------------------------------------------------


def test_deploy_render_ai_endpoint_registered():
    """POST /api/simple/projects/{id}/deploy/render-ai must be a real
    FastAPI route on the creator router."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    assert '@router.post("/projects/{project_id}/deploy/render-ai")' in src, (
        "missing the AI multi-service deploy endpoint"
    )
    assert "async def deploy_project_render_ai" in src


def test_deploy_render_prefill_endpoint_registered():
    """GET /api/simple/projects/{id}/deploy/render-prefill returns the
    Render dashboard URL for the Free-plan redirect."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    assert (
        '@router.get("/projects/{project_id}/deploy/render-prefill")' in src
    ), "missing the prefill endpoint for free-plan redirect"
    assert "async def deploy_project_render_prefill" in src
    assert "dashboard.render.com/select-repo" in src, (
        "prefill must return the Render select-repo URL"
    )


def test_deploy_render_ai_uses_shared_helper():
    """The new endpoint must reuse `_ai_analyze_repo_only` — NOT
    duplicate GitHub-tree-fetch logic."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 5000]
    assert "_ai_analyze_repo_only" in body, (
        "deploy_project_render_ai must call the shared helper, not "
        "re-implement repo analysis"
    )


def test_deploy_render_ai_supports_multi_service():
    """The endpoint must loop over services_plan and call create_service
    per service. Fullstack projects (Detective-1) need 2 services."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert "for svc in services_plan" in body or "for svc in services" in body, (
        "must iterate over services_plan to create one Render service per "
        "AI-recommended service (otherwise fullstack only gets one service)"
    )
    assert "deploy_svc.create_service" in body
    # Both static_site and web_service must be handled
    assert "service_type" in body


def test_deploy_render_ai_reports_empty_env_vars():
    """User experience: AI might emit env vars with empty values (e.g.
    VITE_API_URL). The endpoint must surface them so the user knows
    what to fill in on Render dashboard."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert "empty_env_vars" in body, (
        "response must include empty_env_vars (mirrors Inspector's UX)"
    )


def test_deploy_render_ai_uses_project_repo_not_internal_storage():
    """Critical: AI deploy must use the standalone repo (where the user
    pushed Detective-1), NOT the internal data repo. Internal-storage
    fallback only makes sense for the legacy non-AI deploy_project."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert "project.github_repo_url" in body
    assert "project.github_owner" in body
    # Must NOT hardcode the internal-storage path in the AI variant
    assert 'f"ai-workspace/projects/{project_id}/generated"' not in body, (
        "AI deploy must not fall back to the internal data repo subpath — "
        "AI analyzes the actual user repo (Detective-1), not the data repo"
    )


def test_deploy_render_ai_returns_actionable_no_repo_error():
    """If the user hasn't pushed yet, the AI endpoint must say so clearly
    instead of crashing or silently failing."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert '"error": "no_github_repo"' in body, (
        "must return a structured error so the frontend can route the "
        "user to the «GitHub به push» button"
    )


def test_render_prefill_returns_full_name_and_dashboard_url():
    """Free-plan flow: frontend opens the dashboard URL in a new tab.
    Backend must build the URL with the correct owner/repo slug."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_prefill")
    assert idx != -1
    body = src[idx:idx + 2000]
    assert "render_dashboard_url" in body
    assert "select-repo?type=web&q=" in body, (
        "URL must use the select-repo endpoint with the type=web query "
        "(same pattern Inspector uses)"
    )


# ---------------------------------------------------------------------------
# Frontend modal — source-level pin
# ---------------------------------------------------------------------------


def test_frontend_creator_page_has_deploy_modal():
    """The Creator project page must show a deploy modal with free vs AI
    options, not the old single button that always went through the
    broken single-service path."""
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")

    # Modal state hook
    assert "deployModalOpen" in src, (
        "Creator project page must declare a deployModalOpen state for "
        "the new free-vs-AI modal"
    )
    # Free plan handler
    assert "deployToRenderFreePlan" in src
    # AI plan handler
    assert "deployToRenderAi" in src
    # Both endpoints called
    assert "/deploy/render-prefill" in src
    assert "/deploy/render-ai" in src


def test_frontend_modal_displays_empty_env_var_warnings():
    """The modal must show the empty_env_vars list returned by the
    backend so the user knows what to fill in on Render — same UX as
    Inspector."""
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "empty_env_vars" in src


# ---------------------------------------------------------------------------
# 🐛 Audit fixes — Render API key sourcing, no dead state, etc.
# ---------------------------------------------------------------------------


def test_render_api_key_helper_reads_from_env_and_settings_db():
    """🐛 (audit) Inspector reads Render key from Settings DB
    (`api_key_render`) — the user enters it in the /settings panel and
    it lands there. The original Creator deploy endpoints only checked
    `os.environ` → returned 400 even when the key WAS configured in
    DB. The new helper must check both."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("def _get_render_api_key_value")
    assert idx != -1, "missing _get_render_api_key_value helper"
    body = src[idx:idx + 1500]
    # env first
    assert 'os.environ.get("RENDER_API_KEY"' in body, (
        "must check env var first for fast-path"
    )
    # then Settings DB
    assert "from ...models.setting import Setting" in body
    assert '"api_key_render"' in body, (
        "must check the `api_key_render` Settings DB key (same name "
        "Inspector uses)"
    )


def test_both_deploy_endpoints_use_render_api_key_helper():
    """Both the legacy /deploy and the new /deploy/render-ai endpoints
    must call the helper, NOT call `os.environ.get('RENDER_API_KEY')`
    directly — otherwise the DB-sourced key never gets picked up."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")

    # Both endpoints must call the helper
    for fn_name in ("async def deploy_project(", "async def deploy_project_render_ai("):
        idx = src.find(fn_name)
        assert idx != -1, f"missing {fn_name}"
        # Slice through ~3000 chars or to next @router
        end = src.find("\n@router.", idx + 50)
        body = src[idx:end if end != -1 else idx + 3000]
        assert "_get_render_api_key_value()" in body, (
            f"{fn_name} must call _get_render_api_key_value() so DB-sourced "
            f"keys are picked up — direct os.environ checks miss the panel UX"
        )


def test_render_ai_endpoint_does_not_import_os_locally():
    """Audit cleanup: redundant `import os as _os` was removed — the
    module-level `import os` covers it. Verify the alias is gone so a
    future reader doesn't get confused."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 2000]
    assert "import os as _os" not in body, (
        "redundant local `import os as _os` must be removed — `os` is "
        "already imported at module top"
    )


def test_frontend_no_dead_deploy_url_state():
    """Audit cleanup: the old `deployUrl` / `setDeployUrl` and
    `deploying` / `setDeploying` state were never set after the modal
    refactor (the old `deployToRender` function was replaced). They
    must be removed."""
    src = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    # No setDeployUrl call anywhere — declaration without setter usage
    # means dead state. setDeployUrl appears nowhere now.
    assert "setDeployUrl(" not in src, (
        "setDeployUrl is never called after the modal refactor — the "
        "useState hook should be removed too"
    )
    assert "setDeploying(" not in src, (
        "setDeploying is never called after the modal refactor — the "
        "useState hook should be removed too"
    )


# ---------------------------------------------------------------------------
# 🐛 Empty-Dockerfile guard — root-cause fix for Detective-1 deploy failure
# ---------------------------------------------------------------------------


def test_deploy_render_ai_checks_dockerfile_before_create():
    """User report: AI deployed services with runtime=docker, but Render
    failed with `error: failed to solve: the Dockerfile cannot be empty`
    because Creator engine pushes an empty Dockerfile placeholder (~31
    bytes). The fix: before calling create_service, read the Dockerfile
    from GitHub for each service's root_dir. If empty/missing, override
    the runtime to native Python (backend) or Vite static_site (frontend).
    """
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert "_read_github_file" in body, (
        "must read the Dockerfile from GitHub to verify it's not empty — "
        "AI's recommendation alone is unreliable when Creator emits a "
        "placeholder Dockerfile"
    )
    assert "df_usable" in body, (
        "must compute a df_usable flag based on size + content"
    )


def test_deploy_render_ai_overrides_backend_to_python_native():
    """When the backend's Dockerfile is empty, runtime must be overridden
    to FastAPI/Python native with `pip install -r requirements.txt`."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert 'svc_role == "backend"' in body
    assert "pip install -r requirements.txt" in body, (
        "backend override must use the standard Python build command"
    )
    assert "uvicorn main:app" in body, (
        "backend override must use uvicorn (FastAPI default) as start cmd"
    )


def test_deploy_render_ai_overrides_frontend_to_vite_static_site():
    """When the frontend's Dockerfile is empty, override to static_site
    with the standard Vite build (mirrors Inspector's prompt rules)."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert 'svc_role == "frontend"' in body
    assert '"static_site"' in body, "frontend override must select static_site"
    assert "npm run build" in body
    assert "_redirects" in body, (
        "must include the SPA rewrite rule so client routing works on "
        "Render static sites"
    )


def test_deploy_render_ai_reports_override_in_created_service():
    """The created service entry must carry a flag so the user knows
    the deploy used overridden settings."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert "docker_overridden" in body
    assert "notes_append" in body


def test_deploy_render_ai_dockerfile_usability_threshold():
    """Threshold pinned: > 100 bytes + at least 2 non-comment lines.
    The real-world symptom was 31 bytes — must be flagged as unusable."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def deploy_project_render_ai")
    assert idx != -1
    body = src[idx:idx + 14000]
    assert "len(df_content) > 100" in body
    assert "len(stripped_lines) >= 2" in body
