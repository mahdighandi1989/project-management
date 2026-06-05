"""🎬 Four user-reported regressions on /creator + /project/[id]:

1. Long project description was dumped raw on the project page header
   with no formatting/wrapping. Fix: clamp to 2 lines + open-in-modal.

2. "Re-review with active models before push" feature was REPEATEDLY
   promised but never implemented. User: "تو هم گفتی که انجامش دادی
   ولی الان که پروژه ساخته شده جایی نمیبینم". Fix: real
   /projects/{id}/audit endpoint that consults each active model,
   aggregates findings, and feeds a UI modal with missing files /
   structural issues / goal mismatch / suggestions.

3. project_type="auto" always resolved to FastAPI (then python on
   detect failure). Fix: when auto detect fails, fall back to
   "fullstack" (not "python"), and the detect prompt now teaches the
   AI when to choose fullstack vs single-tier.

4. Generated projects always missed frontend files even for full-stack
   apps (Detective-1 OSINT got only backend). Fix: new "fullstack"
   project_type with both backend/ + frontend/ scaffolding, and the
   structure-generation prompt explicitly demands both halves when
   type == fullstack.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend/src"
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


# ─────────────────────────────────────────────────────────────────────────────
# Issue 1: Description rendering in a modal, not dumped onto the page
# ─────────────────────────────────────────────────────────────────────────────


def test_project_page_clamps_description_and_has_full_modal():
    """Source check — the project page must clamp the description (so it
    doesn't dominate the header) AND offer a 'نمایش کامل' button that
    opens a modal with the full text."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    # Clamp via line-clamp inline style (no extra Tailwind plugin needed)
    assert "WebkitLineClamp" in src, (
        "description must be clamped — otherwise long raw_idea text "
        "dominates the page header"
    )
    # Modal trigger + state
    assert "setDescModalOpen" in src, (
        "the description modal must have a setter so the user can open it"
    )
    assert "نمایش کامل" in src, (
        "the user-facing button text 'نمایش کامل' must remain so the user "
        "can find it"
    )
    # Modal must render the full text inside a pre-wrap block (so the AI's
    # newlines / markdown-y formatting are preserved when expanded)
    assert "whitespace-pre-wrap" in src, (
        "the full-description modal must preserve newlines — not collapse "
        "them into a single paragraph like the broken inline view did"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Issue 2: Pre-push audit endpoint + UI button
# ─────────────────────────────────────────────────────────────────────────────


def test_audit_endpoint_is_registered():
    """Backend: POST /projects/{id}/audit must exist."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    assert '@router.post("/projects/{project_id}/audit")' in src, (
        "the audit endpoint MUST be registered on the simple_projects "
        "router — that's the feature the user repeatedly asked for"
    )
    assert "async def audit_project" in src
    # Must consult AI manager + aggregate per-model findings
    assert "results_per_model" in src or "per_model" in src
    assert "overall_score" in src, (
        "audit must produce a quantitative score so the user has a "
        "summary number — not just a wall of text"
    )


def test_audit_endpoint_uses_all_active_models_by_default():
    """When the caller doesn't specify model_ids, audit consults ALL
    currently-active models so the user gets multi-perspective audit
    (parity with how the create flow uses the same model set)."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    assert idx != -1
    body = src[idx:idx + 5000]
    # The default branch must enumerate available models
    assert "get_available_models" in body, (
        "audit must default to all available models — otherwise users "
        "have to manually pick which models to consult"
    )


def test_audit_endpoint_handles_empty_model_list():
    """If no AI models are configured at all, return a clear 400 — not
    a stacktrace or a fake 'audit success' with zero models consulted."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    body = src[idx:idx + 5000]
    assert "هیچ مدل" in body or "status_code=400" in body, (
        "audit must explicitly return 400 when no models are configured"
    )


def test_project_page_has_audit_button():
    """Frontend: the audit button must be in the project header.
    Otherwise the user CAN'T trigger the audit even if the backend
    works — which is exactly what they complained about."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "بررسی مجدد قبل از push" in src, (
        "the audit button must show the user-facing Persian label so "
        "the user can find it on the project page"
    )
    assert "runAudit" in src
    # Must call the /audit endpoint
    assert "/audit" in src and "method: 'POST'" in src


def test_project_page_audit_modal_shows_findings_and_score():
    """The audit modal must surface the rich aggregated output —
    missing files, structural issues, score — not just a yes/no."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "missing_critical_files" in src, (
        "audit modal must display missing_critical_files — that's the "
        "main signal for 'should I push or fix first?'"
    )
    assert "structural_issues" in src
    assert "goal_mismatch_reasons" in src
    assert "overall_score_avg" in src


def test_project_page_has_push_to_github_button():
    """The user also said push-to-GitHub was missing as a button. The
    audit modal offers a 'push anyway' option, but a standalone push
    button must exist too for users who already trust the result."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "push به GitHub" in src or "pushToGithub" in src
    assert "/push-to-github" in src


# ─────────────────────────────────────────────────────────────────────────────
# Issue 3 + 4: auto-detect leads to fullstack when appropriate
# ─────────────────────────────────────────────────────────────────────────────


def test_fullstack_structure_template_exists():
    """The default-structure dict MUST contain a 'fullstack' key with
    BOTH backend/ and frontend/ directories. Previously the dict only
    had single-tier templates and auto-detect for OSINT/dashboard
    projects fell through to python (backend-only)."""
    from app.services.simple_creator import SimpleProjectCreator
    creator = SimpleProjectCreator()
    fs = creator._get_default_structure("fullstack")
    dirs = fs.get("directories") or []
    assert any("backend" in d for d in dirs), (
        "fullstack structure must include backend/ directories"
    )
    assert any("frontend" in d for d in dirs), (
        "fullstack structure must include frontend/ directories — "
        "this is the architectural gap the user reported"
    )
    files = [f.get("path", "") for f in (fs.get("files") or [])]
    # Both halves must have entry-point files
    assert any("backend/app/main.py" in f for f in files), (
        "fullstack must include backend/app/main.py (FastAPI entry)"
    )
    assert any("frontend/src/app/page.tsx" in f for f in files), (
        "fullstack must include frontend/src/app/page.tsx (Next.js page)"
    )
    # Bridge: API client in frontend so it can talk to backend
    assert any("frontend/src/lib/api" in f for f in files), (
        "fullstack must include a frontend API client so the UI knows "
        "how to call the backend"
    )


def test_fullstack_accepts_hyphen_alias():
    """AI might emit 'full-stack' (with hyphen) instead of 'fullstack'.
    The structure lookup must accept both."""
    from app.services.simple_creator import SimpleProjectCreator
    creator = SimpleProjectCreator()
    a = creator._get_default_structure("fullstack")
    b = creator._get_default_structure("full-stack")
    assert a["directories"] == b["directories"]
    assert a["files"] == b["files"]


def test_auto_detect_fallback_is_fullstack_not_python():
    """When auto-detect fails (AI down, parse error), the fallback must
    be 'fullstack' — generating both halves is much easier for the user
    to delete unused files than to manually add a missing frontend.
    Previously the fallback was 'python' which gave a CLI scaffold for
    web-app requests."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    # Find the auto-detect fallback block
    idx = src.find("auto-detect failed")
    assert idx != -1
    body = src[idx:idx + 800]
    assert 'project_type = "fullstack"' in body, (
        "auto-detect failure fallback must be 'fullstack', not 'python' — "
        "users selecting 'auto' for web apps were getting CLI scaffolds"
    )


def test_detect_prompt_mentions_fullstack_with_keywords():
    """The detect-type AI prompt must explicitly tell the AI when to
    prefer fullstack (dashboard, OSINT, CRM, admin panel, etc.).
    Otherwise even good AIs default to fastapi for ambiguous requests."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def _detect_project_type")
    body = src[idx:idx + 3000]
    assert "fullstack" in body, (
        "detect prompt must list 'fullstack' as an option for the AI"
    )
    # Persian or English signal keywords that hint at full-stack
    assert "داشبورد" in body or "dashboard" in body, (
        "detect prompt must include keyword hints for when fullstack is "
        "the right choice"
    )


def test_valid_types_includes_fullstack():
    """The validation set for primary_type must include 'fullstack' so
    the detect AI's output isn't silently coerced back to 'python'."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("valid_types = {")
    assert idx != -1
    body = src[idx:idx + 400]
    assert '"fullstack"' in body, (
        "valid_types must include 'fullstack' — otherwise the AI's "
        "fullstack picks are coerced to python by the validation step"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Issue 2 end-to-end: audit endpoint executes without crashing on edge cases
# ─────────────────────────────────────────────────────────────────────────────


def _make_fake_project(monkeypatch):
    """Stash a fake project in the singleton creator's in-memory dict."""
    from app.services.simple_creator import get_simple_creator, Project, ProjectFile
    creator = get_simple_creator()
    proj = Project(
        id="proj_audit_test_123",
        name="TestApp",
        description="A test project for auditing.",
        project_type="fullstack",
        technologies=["FastAPI", "Next.js"],
        status="created",
        files=[
            ProjectFile(
                path="backend/app/main.py",
                content="from fastapi import FastAPI\napp = FastAPI()\n",
                language="python",
            ),
            ProjectFile(
                path="frontend/src/app/page.tsx",
                content="export default function Page() { return <div/>; }",
                language="typescript",
            ),
        ],
        structure={
            "directories": ["backend", "frontend"],
            "entry_point": "backend/app/main.py",
            "run_command": "docker compose up",
        },
    )
    creator.projects[proj.id] = proj
    return proj


@pytest.mark.asyncio
async def test_audit_endpoint_handles_well_formed_json_responses(monkeypatch):
    """The happy path: each model returns valid JSON. Endpoint should
    aggregate cleanly and return the expected response shape."""
    from app.api.routes.simple_projects import audit_project, AuditProjectRequest
    from app.services.simple_creator import Project, ProjectFile

    proj = _make_fake_project(monkeypatch)

    async def fake_ai_generate(prompt, model_ids=None):
        return (
            '{"overall_score": 85, "ready_to_push": true, '
            '"matches_goal": true, '
            '"missing_critical_files": ["docker-compose.yml"], '
            '"structural_issues": [], "quality_concerns": [], '
            '"goal_mismatch_reasons": [], '
            '"suggestions_before_push": ["add CI"], '
            '"summary": "Solid."}'
        )

    class _FakeModel:
        def __init__(self, mid): self.id = mid

    class _FakeMgr:
        def get_available_models(self, task_type=None):
            return [_FakeModel("m1"), _FakeModel("m2")]

    with patch(
        "app.services.ai_manager.get_ai_manager",
        return_value=_FakeMgr(),
    ), patch(
        "app.api.routes.simple_projects.ai_generate",
        side_effect=fake_ai_generate,
    ):
        result = await audit_project(proj.id, AuditProjectRequest(model_ids=[]))

    assert result["success"] is True
    assert result["aggregated"]["models_succeeded"] == 2
    assert result["aggregated"]["overall_score_avg"] == 85
    assert result["aggregated"]["ready_to_push_majority"] is True
    assert "docker-compose.yml" in result["aggregated"]["missing_critical_files"]


@pytest.mark.asyncio
async def test_audit_endpoint_survives_string_score_and_list_response(monkeypatch):
    """🚨 Edge cases the previous version would CRASH on:
      - score returned as '85/100' string → int() raised
      - AI returns a JSON list at top level instead of dict → .get() raised
      - score field is missing entirely → None × 0 raised TypeError

    Defensive coercion must keep the endpoint working."""
    from app.api.routes.simple_projects import audit_project, AuditProjectRequest

    proj = _make_fake_project(monkeypatch)

    call_count = {"n": 0}

    async def fake_ai_generate(prompt, model_ids=None):
        call_count["n"] += 1
        # Model 1: score as fraction string + missing some keys
        if call_count["n"] == 1:
            return (
                '{"overall_score": "85/100", "ready_to_push": true, '
                '"missing_critical_files": ["x"]}'
            )
        # Model 2: AI emitted a list at top level (bad model behavior)
        if call_count["n"] == 2:
            return '[{"this": "is an array"}]'
        # Model 3: score missing, lists of non-strings
        return (
            '{"matches_goal": false, '
            '"structural_issues": [42, null, "real string"], '
            '"summary": "..."}'
        )

    class _FakeModel:
        def __init__(self, mid): self.id = mid

    class _FakeMgr:
        def get_available_models(self, task_type=None):
            return [_FakeModel("m1"), _FakeModel("m2"), _FakeModel("m3")]

    with patch(
        "app.services.ai_manager.get_ai_manager",
        return_value=_FakeMgr(),
    ), patch(
        "app.api.routes.simple_projects.ai_generate",
        side_effect=fake_ai_generate,
    ):
        result = await audit_project(proj.id, AuditProjectRequest(model_ids=[]))

    # Must NOT have crashed
    assert result["success"] is True
    # Model 1 gave 85 (parsed from "85/100"), Model 3 gave 0 (missing),
    # Model 2's list response was skipped as non-dict → not counted
    assert result["aggregated"]["models_succeeded"] == 2
    # avg = (85 + 0) / 2 = 42-43
    assert 40 <= result["aggregated"]["overall_score_avg"] <= 45
    # The string item in structural_issues must survive; non-strings filtered
    assert "real string" in result["aggregated"]["structural_issues"]
    # Non-strings shouldn't appear as literal "42" only if we coerced ok
    # (the defensive code keeps str-coerced numbers; both behaviors fine,
    # but it must NOT have crashed)


@pytest.mark.asyncio
async def test_audit_endpoint_runs_models_in_parallel():
    """🚨 Sequential audit would take >100s for 5 models which exceeds
    Render's gateway timeout. The endpoint must use asyncio.gather so
    all model calls happen concurrently."""
    import asyncio as _asyncio
    import time
    from app.api.routes.simple_projects import audit_project, AuditProjectRequest
    from app.services.simple_creator import get_simple_creator, Project, ProjectFile

    proj = Project(
        id="proj_parallel_test_999",
        name="ParTest",
        description="parallel audit test",
        project_type="fullstack",
        files=[ProjectFile(path="a.py", content="x", language="python")],
    )
    creator = get_simple_creator()
    creator.projects[proj.id] = proj

    async def slow_ai_generate(prompt, model_ids=None):
        await _asyncio.sleep(0.5)  # each call takes 0.5s
        return '{"overall_score": 70, "ready_to_push": true}'

    class _FakeModel:
        def __init__(self, mid): self.id = mid

    class _FakeMgr:
        def get_available_models(self, task_type=None):
            return [_FakeModel(f"m{i}") for i in range(5)]

    started = time.time()
    with patch(
        "app.services.ai_manager.get_ai_manager",
        return_value=_FakeMgr(),
    ), patch(
        "app.api.routes.simple_projects.ai_generate",
        new=slow_ai_generate,
    ):
        result = await audit_project(proj.id, AuditProjectRequest(model_ids=[]))
    elapsed = time.time() - started

    assert result["aggregated"]["models_succeeded"] == 5
    # Sequential: 5 × 0.5s = 2.5s+. Parallel: ~0.5s + overhead.
    # Allow some slack but enforce < 1.5s (clearly parallel).
    assert elapsed < 1.5, (
        f"audit took {elapsed:.2f}s for 5 models × 0.5s — must be parallel "
        f"(asyncio.gather), not sequential, or Render gateway times out"
    )


@pytest.mark.asyncio
async def test_audit_endpoint_404_on_unknown_project():
    """If project doesn't exist, must return 404 — not 500 or crash."""
    from app.api.routes.simple_projects import audit_project, AuditProjectRequest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        await audit_project(
            "proj_does_not_exist_xyz",
            AuditProjectRequest(model_ids=[]),
        )
    assert ei.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Hyphen alias normalization at the create-route level (not only detect)
# ─────────────────────────────────────────────────────────────────────────────


def test_full_stack_hyphen_normalization_works_without_auto_detect():
    """🚨 Bug found during audit pass: the 'full-stack' → 'fullstack'
    normalization was INSIDE the auto-detect branch. If a user posted
    project_type='full-stack' with auto_detect_type=False, the
    normalization never ran and the structure lookup fell to python.
    Source check: the normalization must be OUTSIDE that branch."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    # Find the normalization line
    idx = src.find('if project_type == "full-stack"')
    assert idx != -1
    # Walk back to find the enclosing `if request.auto_detect_type`
    before = src[:idx]
    block_start = before.rfind("if request.auto_detect_type")
    assert block_start != -1
    # Count indent of both blocks
    block_indent = len(src[block_start:].split("\n")[0]) - len(
        src[block_start:].split("\n")[0].lstrip()
    )
    norm_indent = len(src[idx:].split("\n")[0]) - len(
        src[idx:].split("\n")[0].lstrip()
    )
    # Normalization indent must be <= block indent (i.e., not deeper into
    # the auto-detect branch).
    assert norm_indent <= block_indent, (
        "the full-stack→fullstack normalization must NOT be nested inside "
        "the `if request.auto_detect_type` branch — otherwise users posting "
        "project_type='full-stack' directly bypass it"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Apply-fixes endpoint — the auto-fix that user explicitly asked for
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_fixes_endpoint_generates_missing_files(tmp_path):
    """When the user clicks the auto-fix button with explicit
    missing_files, the endpoint must generate them via _generate_file
    and persist both on disk and in project.files. Idempotent: paths
    that already exist must NOT be regenerated (no silent overwrite)."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    # Use the test's tmp_path so we don't pollute the real workspace
    creator.workspace = tmp_path

    proj = Project(
        id="proj_fix_test_111",
        name="DetectiveTest",
        description="OSINT analysis platform",
        project_type="fastapi",
        files=[
            ProjectFile(
                path="backend/app/main.py",
                content="# existing",
                language="python",
            ),
        ],
    )
    creator.projects[proj.id] = proj

    async def fake_ai_generate(prompt, model_ids=None):
        return f"# generated content for: {prompt[:40]}"

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                missing_files=[
                    "frontend/src/app/page.tsx — main page",
                    "frontend/package.json",
                    "backend/app/main.py",  # already exists → must skip
                ],
            ),
        )

    assert result["success"] is True
    added_paths = [f["path"] for f in result["files_added"]]
    assert "frontend/src/app/page.tsx" in added_paths, (
        "the auto-fix must parse the path out of free-form audit findings "
        "like 'frontend/src/app/page.tsx — main page'"
    )
    assert "frontend/package.json" in added_paths
    # The existing file must be skipped, not overwritten
    skipped_paths = [s["path"] for s in result["files_skipped"]]
    assert "backend/app/main.py" in skipped_paths, (
        "existing files must be skipped — the auto-fix is idempotent"
    )
    # Files should be physically on disk now
    assert (tmp_path / "proj_fix_test_111" / "frontend/src/app/page.tsx").exists()
    # project.files in-memory must include the new ones
    paths_in_proj = [f.path for f in proj.files]
    assert "frontend/src/app/page.tsx" in paths_in_proj


@pytest.mark.asyncio
async def test_apply_fixes_can_promote_to_fullstack(tmp_path):
    """The user's Detective-1 scenario: project was created as fastapi,
    audit said "this needs frontend too". The user clicks "ارتقا به
    fullstack" — the endpoint must:
      1. Switch project.project_type to 'fullstack'
      2. Generate every fullstack-template file that doesn't already
         exist (without touching the ones that do)
      3. Update the structure metadata"""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_promote_222",
        name="UpgradeTest",
        description="something that needs both halves",
        project_type="fastapi",
        files=[
            ProjectFile(
                path="backend/app/main.py",
                content="# existing backend",
                language="python",
            ),
        ],
    )
    creator.projects[proj.id] = proj

    async def fake_ai_generate(prompt, model_ids=None):
        return "// generated\n"

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(upgrade_to_fullstack=True),
        )

    assert result["promoted_to_fullstack"] is True
    assert proj.project_type == "fullstack", (
        "project_type must update so future regenerations honor fullstack"
    )
    added_paths = [f["path"] for f in result["files_added"]]
    # Frontend files from the fullstack template must be added
    assert "frontend/src/app/page.tsx" in added_paths
    assert "frontend/package.json" in added_paths
    # The pre-existing backend file must NOT be regenerated — verify by
    # checking that backend/app/main.py is NOT in the added list AND the
    # original content is intact (no silent overwrite).
    assert "backend/app/main.py" not in added_paths, (
        "existing files must not be re-added — the promote path skips "
        "them before they ever enter the generation queue"
    )
    existing = next(
        (f for f in proj.files if f.path == "backend/app/main.py"), None,
    )
    assert existing is not None
    assert existing.content == "# existing backend", (
        "existing file content must be preserved verbatim — auto-fix "
        "is additive only, never destructive"
    )


@pytest.mark.asyncio
async def test_apply_fixes_404_on_unknown_project():
    """Same HTTP semantics as audit — unknown project → 404."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await apply_audit_fixes(
            "proj_unknown_xyz",
            ApplyAuditFixesRequest(missing_files=["a.py"]),
        )
    assert ei.value.status_code == 404


def test_parse_clean_path_extracts_paths_from_audit_findings():
    """Audit findings come back as free-form strings:
       'frontend/src/app/page.tsx چون پروژه نیاز به UI دارد'
       'docker-compose.yml باید اضافه شود'
       '`requirements.txt` با dependency های جدید'
    The parser must extract just the path, ignoring the prose."""
    from app.api.routes.simple_projects import _parse_clean_path

    assert _parse_clean_path("frontend/src/app/page.tsx چون UI لازم است") == (
        "frontend/src/app/page.tsx"
    )
    assert _parse_clean_path("`requirements.txt` با dep جدید") == (
        "requirements.txt"
    )
    assert _parse_clean_path("docker-compose.yml") == "docker-compose.yml"
    # Garbage input → None (not a crash)
    assert _parse_clean_path("") is None
    assert _parse_clean_path("just a sentence") is None


# ─────────────────────────────────────────────────────────────────────────────
# Full CRUD: modify + delete (user explicitly asked for this in audit pass 3)
# ─────────────────────────────────────────────────────────────────────────────


def test_audit_prompt_requests_modify_and_delete_lists():
    """The audit prompt must explicitly ask each AI for files_to_modify
    (existing files with wrong content) AND files_to_delete (extra
    files that shouldn't exist). Without this, the AI only ever flags
    missing files — user can't get edit/delete from the audit."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    body = src[idx:idx + 8000]
    assert "files_to_modify" in body, (
        "audit prompt must request files_to_modify so the AI flags existing "
        "files with wrong content (not just missing ones)"
    )
    assert "files_to_delete" in body, (
        "audit prompt must request files_to_delete so the AI flags extra "
        "files that should be removed"
    )
    # The prompt must give the AI a structured format for each so the
    # apply-fixes step can parse it correctly
    assert "issue" in body and "suggestion" in body, (
        "modify entries must have 'issue' and 'suggestion' fields so "
        "regeneration can target the specific problem the AI flagged"
    )
    assert "reason" in body, (
        "delete entries must include 'reason' so user sees WHY before "
        "approving the destructive action"
    )


def test_aggregation_includes_modify_and_delete_categories():
    """The aggregated response shape must expose files_to_modify and
    files_to_delete so the frontend can render them and accept user
    selections."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("aggregated = {")
    assert idx != -1
    body = src[idx:idx + 1500]
    assert '"files_to_modify"' in body
    assert '"files_to_delete"' in body


@pytest.mark.asyncio
async def test_apply_fixes_regenerates_existing_files_with_audit_context(tmp_path):
    """🚨 The user's specific concern: 'ویرایش و حذف و اضافه انجام میده؟'
    — does it edit existing files, not just add missing ones?

    When files_to_modify is passed, the existing file content must be
    OVERWRITTEN with regenerated content. The regeneration prompt must
    include the audit's 'issue' and 'suggestion' so the new content
    addresses what was wrong, not just a fresh generation."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest, FileToModify,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_modify_333",
        name="ModTest",
        description="needs proper routes",
        project_type="fastapi",
        files=[
            ProjectFile(
                path="backend/app/main.py",
                content="# stub — no routes registered",
                language="python",
            ),
        ],
    )
    creator.projects[proj.id] = proj
    # Pre-write the file to disk so the modify path has something to
    # overwrite (would normally have been written at create time).
    proj_dir = tmp_path / proj.id
    (proj_dir / "backend/app").mkdir(parents=True, exist_ok=True)
    (proj_dir / "backend/app/main.py").write_text("# stub")

    captured_prompts: List[str] = []

    async def fake_ai_generate(prompt, model_ids=None):
        captured_prompts.append(prompt)
        return "from fastapi import FastAPI\napp = FastAPI()\napp.include_router(...)"

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                files_to_modify=[
                    FileToModify(
                        path="backend/app/main.py",
                        issue="routes not registered",
                        suggestion="add include_router for auth, users",
                    ),
                ],
            ),
        )

    modified_paths = [f["path"] for f in result["files_modified"]]
    assert "backend/app/main.py" in modified_paths, (
        "modify request must update the existing file, not skip it"
    )
    # The new content must have actually replaced the old
    updated = next(f for f in proj.files if f.path == "backend/app/main.py")
    assert "include_router" in updated.content
    assert "stub" not in updated.content
    # Disk must reflect the new content too
    on_disk = (proj_dir / "backend/app/main.py").read_text()
    assert "include_router" in on_disk
    # Crucially: the regeneration prompt must mention the audit's
    # `issue` so the AI doesn't just write a generic main.py
    assert any("routes not registered" in p for p in captured_prompts), (
        "the regen prompt must include the audit's `issue` note so the "
        "new content addresses what was specifically wrong"
    )
    assert any("include_router for auth" in p for p in captured_prompts), (
        "the regen prompt must include the audit's `suggestion` so the "
        "AI knows what the fix should look like"
    )


@pytest.mark.asyncio
async def test_apply_fixes_deletes_listed_files(tmp_path):
    """When files_to_delete is provided, those paths must be removed
    from disk AND from project.files metadata. Files not listed must
    remain untouched."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_delete_444",
        name="DelTest",
        description="cleanup test",
        project_type="fastapi",
        files=[
            ProjectFile(path="keep.py", content="# keep me", language="python"),
            ProjectFile(path="remove.py", content="# delete me", language="python"),
        ],
    )
    creator.projects[proj.id] = proj
    proj_dir = tmp_path / proj.id
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "keep.py").write_text("# keep me")
    (proj_dir / "remove.py").write_text("# delete me")

    result = await apply_audit_fixes(
        proj.id,
        ApplyAuditFixesRequest(files_to_delete=["remove.py"]),
    )

    deleted_paths = [f["path"] for f in result["files_deleted"]]
    assert "remove.py" in deleted_paths
    # Disk: removed
    assert not (proj_dir / "remove.py").exists()
    # Disk: kept
    assert (proj_dir / "keep.py").exists()
    # Metadata: removed
    paths_now = [f.path for f in proj.files]
    assert "remove.py" not in paths_now
    assert "keep.py" in paths_now


@pytest.mark.asyncio
async def test_apply_fixes_delete_rejects_path_traversal(tmp_path):
    """Safety: deleting `../../etc/passwd` must NOT escape the project
    workspace. Path-traversal must be rejected with a skip reason."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_traversal_555",
        name="SafetyTest",
        description="x",
        project_type="fastapi",
    )
    creator.projects[proj.id] = proj
    (tmp_path / proj.id).mkdir(parents=True, exist_ok=True)
    # Plant a file outside the project workspace
    (tmp_path / "outside_target.txt").write_text("DO NOT DELETE")

    result = await apply_audit_fixes(
        proj.id,
        ApplyAuditFixesRequest(files_to_delete=["../outside_target.txt"]),
    )

    # The file outside the project MUST still exist
    assert (tmp_path / "outside_target.txt").exists(), (
        "path traversal must be blocked — files outside the project "
        "workspace must never be deleted via this endpoint"
    )
    # The traversal attempt must be reported as skipped
    skipped_reasons = " ".join(s.get("reason", "") for s in result["files_skipped"])
    assert "outside" in skipped_reasons.lower(), (
        "the skip reason must mention 'outside' so frontend can show "
        "a clear error"
    )


@pytest.mark.asyncio
async def test_apply_fixes_treats_missing_target_as_add_not_modify(tmp_path):
    """Soft promotion: if user requests modify on a path that doesn't
    exist (audit can be stale, or user picked the wrong category),
    treat it as an "add" — don't silently drop the request."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest, FileToModify,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_softpromo_666",
        name="SoftTest",
        description="x",
        project_type="fastapi",
    )
    creator.projects[proj.id] = proj
    (tmp_path / proj.id).mkdir(parents=True, exist_ok=True)

    async def fake_ai_generate(prompt, model_ids=None):
        return "new content"

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                files_to_modify=[
                    FileToModify(path="new_file.py", issue="x", suggestion="y"),
                ],
            ),
        )

    # Should appear in files_added (not skipped or lost)
    added_paths = [f["path"] for f in result["files_added"]]
    assert "new_file.py" in added_paths, (
        "modify request on non-existent path must fall through to add — "
        "otherwise stale audit silently drops user intent"
    )


def test_frontend_audit_modal_has_modify_and_delete_sections():
    """Source check — the modal must surface the new modify and delete
    categories with checkboxes (per-item opt-in, especially for delete)."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "files_to_modify" in src and "files_to_delete" in src, (
        "modal must render both new categories from aggregated audit"
    )
    # Per-item checkboxes
    assert "selectedModifies" in src and "selectedDeletes" in src, (
        "per-item state for which modifies/deletes to apply"
    )
    # Destructive action MUST have explicit confirmation
    assert "confirm(" in src, (
        "delete action must wrap in confirm() — destructive ops need "
        "explicit acknowledgement before submitting"
    )
    # Default: delete is OPT-IN (selectedDeletes starts empty)
    assert "new Set()" in src or "Set<string>(new Set())" in src or "setSelectedDeletes(new Set" in src


def test_frontend_audit_modal_has_apply_fixes_buttons():
    """Source-grep: the audit modal must surface the auto-fix buttons,
    not just report findings. User: 'این موضوع رو هم بررسی و در صورت
    نیاز اصلاح میکنه؟' — yes, via these buttons."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    # Must call the apply-fixes endpoint
    assert "/apply-fixes" in src, (
        "frontend must POST to /apply-fixes — without this the user "
        "sees the audit findings but has no way to actually fix anything"
    )
    # Both action buttons (just missing files, OR promote to fullstack)
    assert "applyAuditFixes" in src
    assert "upgrade_to_fullstack" in src or "upgradeFullstack" in src, (
        "must offer the 'promote to fullstack' shortcut so a backend-only "
        "project can be upgraded in-place (Detective-1 use case)"
    )
    assert "تولید" in src and "فایل" in src and "مفقود" in src, (
        "the auto-fix button must be labeled clearly in Persian so user "
        "knows what it does"
    )


def test_structure_prompt_demands_both_halves_for_fullstack():
    """When project_type=fullstack, the structure-generation prompt
    must explicitly REQUIRE both backend/ and frontend/ — otherwise
    the AI defaults to its training prior of 'fastapi → backend only'."""
    src = (
        _BACKEND_ROOT / "app/services/simple_creator.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def _generate_structure")
    body = src[idx:idx + 3000]
    assert "fullstack" in body
    assert "backend/" in body and "frontend/" in body, (
        "the fullstack guidance must mention both backend/ and frontend/ "
        "directories so the AI knows the structure is mandatory bilateral"
    )
