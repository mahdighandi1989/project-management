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
    """Stash a fake project in the singleton creator's in-memory dict.

    Also redirect the creator's workspace to a temp dir for the duration
    of the test — otherwise audit/apply will persist project.json into
    the real backend/storage/projects/ tree and pollute the repo. We
    create the temp dir, point the singleton at it, and rely on pytest's
    monkeypatch undo to restore the original workspace after the test.
    """
    import tempfile
    from pathlib import Path as _PathTest
    from app.services.simple_creator import get_simple_creator, Project, ProjectFile
    creator = get_simple_creator()
    tmpdir = _PathTest(tempfile.mkdtemp(prefix="creator_audit_test_"))
    monkeypatch.setattr(creator, "workspace", tmpdir)
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

    async def fake_ai_generate(prompt, model_ids=None, **kwargs):
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

    async def fake_ai_generate(prompt, model_ids=None, **kwargs):
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
async def test_audit_endpoint_runs_models_in_parallel(monkeypatch, tmp_path):
    """🚨 Sequential audit would take >100s for 5 models which exceeds
    Render's gateway timeout. The endpoint must use asyncio.gather so
    all model calls happen concurrently."""
    import asyncio as _asyncio
    import time
    from app.api.routes.simple_projects import audit_project, AuditProjectRequest
    from app.services.simple_creator import get_simple_creator, Project, ProjectFile

    # Redirect workspace so audit's history-persistence side effect
    # doesn't pollute the real backend/storage/projects/ tree.
    monkeypatch.setattr(get_simple_creator(), "workspace", tmp_path)

    proj = Project(
        id="proj_parallel_test_999",
        name="ParTest",
        description="parallel audit test",
        project_type="fullstack",
        files=[ProjectFile(path="a.py", content="x", language="python")],
    )
    creator = get_simple_creator()
    creator.projects[proj.id] = proj

    async def slow_ai_generate(prompt, model_ids=None, **kwargs):
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

    async def fake_ai_generate(prompt, model_ids=None, **kwargs):
        return f"# generated content for: {prompt[:40]}"

    async def fake_ai_generate_with_meta(prompt, model_ids=None, **kwargs):
        return (await fake_ai_generate(prompt, model_ids), "fake-test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_ai_generate_with_meta,
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

    async def fake_ai_generate(prompt, model_ids=None, **kwargs):
        return "// generated\n"

    async def fake_ai_generate_with_meta(prompt, model_ids=None, **kwargs):
        return ("// generated\n", "fake-test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_ai_generate_with_meta,
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
    # Window widened from 8000 → 14000 chars because the audit prompt
    # now embeds previous-audit context + per-file priority sort + a
    # truncation note before the JSON schema example. The "issue" /
    # "suggestion" / "reason" markers live in the JSON example near
    # the end.
    body = src[idx:idx + 14000]
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

    async def fake_ai_generate(prompt, model_ids=None, **kwargs):
        captured_prompts.append(prompt)
        return "from fastapi import FastAPI\napp = FastAPI()\napp.include_router(...)"

    async def fake_ai_generate_with_meta(prompt, model_ids=None, **kwargs):
        content = await fake_ai_generate(prompt, model_ids)
        return (content, "fake-test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_ai_generate_with_meta,
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

    async def fake_ai_generate(prompt, model_ids=None, **kwargs):
        return "new content"

    async def fake_ai_generate_with_meta(prompt, model_ids=None, **kwargs):
        return ("new content", "fake-test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_ai_generate,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_ai_generate_with_meta,
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


# ─────────────────────────────────────────────────────────────────────────────
# Model attribution — user asked: "امضاشون پای کار ثبت می‌شه؟"
# ─────────────────────────────────────────────────────────────────────────────


def test_project_file_dataclass_has_attribution_fields():
    """The ProjectFile dataclass must have generated_by + generated_at
    so the per-file attribution can be persisted. Without these, UI
    can't show 'این فایل توسط claude نوشته شد' even if the backend
    knows."""
    from app.services.simple_creator import ProjectFile
    from dataclasses import fields
    field_names = {f.name for f in fields(ProjectFile)}
    assert "generated_by" in field_names, (
        "ProjectFile must have generated_by — user explicitly asked "
        "'امضاشون پای کار ثبت می‌شه؟'"
    )
    assert "generated_at" in field_names


def test_project_file_to_dict_includes_attribution():
    """The JSON serialization must include the attribution fields so
    the frontend receives them via /api/simple/projects/{id}."""
    from app.services.simple_creator import ProjectFile
    f = ProjectFile(
        path="main.py", content="x", language="python",
        generated_by="claude-sonnet-4-6", generated_at="2026-06-05T12:00",
    )
    d = f.to_dict()
    assert d.get("generated_by") == "claude-sonnet-4-6"
    assert d.get("generated_at") == "2026-06-05T12:00"


def test_ai_generate_with_meta_returns_tuple():
    """The new meta variant must return (content, model_id) — not just
    a string. This is the contract simple_creator's
    _tracked_ai_generate relies on for attribution."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    assert "async def ai_generate_with_meta" in src, (
        "ai_generate_with_meta must exist — that's the attribution-aware "
        "variant. Without it, no per-file model recording is possible."
    )
    # The function must return a tuple. Cheapest source check:
    idx = src.find("async def ai_generate_with_meta")
    body = src[idx:idx + 3000]
    assert "return content, effective_id" in body or "return content, mid" in body, (
        "ai_generate_with_meta must return a tuple of (content, model_id)"
    )


@pytest.mark.asyncio
async def test_apply_fixes_records_model_attribution_on_new_files(tmp_path):
    """When apply-fixes generates a missing file, the generated_by
    field on the new ProjectFile must contain the model that produced
    it. This is the audit trail the user explicitly asked for."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_attribution_777",
        name="AttrTest",
        description="x",
        project_type="fastapi",
    )
    creator.projects[proj.id] = proj
    (tmp_path / proj.id).mkdir(parents=True, exist_ok=True)

    async def fake_with_meta(prompt, model_ids=None):
        # Simulate the real contract: return (content, used_model_id)
        return ("// new content", "test-model-claude")

    async def fake_legacy(prompt, model_ids=None):
        return "// new content"

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_with_meta,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(missing_files=["src/app/page.tsx"]),
        )

    # The result must surface the attribution
    added = next(
        (f for f in result["files_added"] if f["path"] == "src/app/page.tsx"),
        None,
    )
    assert added is not None
    assert added.get("generated_by") == "test-model-claude", (
        "files_added entry must include generated_by so the UI can "
        "display which model produced each file"
    )
    # And the ProjectFile in memory must carry it too
    pf = next((f for f in proj.files if f.path == "src/app/page.tsx"), None)
    assert pf is not None
    assert pf.generated_by == "test-model-claude"


@pytest.mark.asyncio
async def test_apply_fixes_records_attribution_on_modify(tmp_path):
    """Same attribution on the regenerate path — when an existing file
    is rewritten, generated_by updates to the model that did the
    rewrite."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest, FileToModify,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_attribution_modify_888",
        name="ModAttrTest",
        description="x",
        project_type="fastapi",
        files=[
            ProjectFile(
                path="main.py",
                content="# old",
                language="python",
                generated_by="old-model",
            ),
        ],
    )
    creator.projects[proj.id] = proj
    proj_dir = tmp_path / proj.id
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "main.py").write_text("# old")

    async def fake_legacy(prompt, model_ids=None):
        return "# new"

    async def fake_with_meta(prompt, model_ids=None):
        return ("# new", "new-model-gemini")

    with patch(
        "app.api.routes.simple_projects.ai_generate",
        new=fake_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_with_meta,
    ):
        await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                files_to_modify=[
                    FileToModify(path="main.py", issue="needs upgrade", suggestion="add typing"),
                ],
            ),
        )

    pf = next(f for f in proj.files if f.path == "main.py")
    assert pf.generated_by == "new-model-gemini", (
        "after a regenerate, generated_by must reflect the model that "
        "did the rewrite — not the original model"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Frontend honors creator's model selection
# ─────────────────────────────────────────────────────────────────────────────


def test_frontend_audit_reads_selected_models_from_localstorage():
    """🚨 The bug the user spotted: frontend was sending model_ids=[]
    which means 'use all active'. The fix must read the same
    localStorage key the /creator page writes so the user's selection
    carries over to audit + apply-fixes."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "creator_selected_models" in src, (
        "project page must read the same localStorage key the /creator "
        "page uses so user's model selection is honored on the project "
        "detail page (audit / apply-fixes)"
    )
    assert "getSelectedModelIds" in src
    # The audit POST and apply-fixes POST must use it
    runaudit_idx = src.find("const runAudit")
    fix_idx = src.find("applyAuditFixes")
    # Both should call getSelectedModelIds
    assert "getSelectedModelIds()" in src
    # And the body should NOT hardcode `model_ids: []`
    # (search around the audit + apply fetches)
    assert "body: JSON.stringify({ model_ids: [] })" not in src, (
        "must not hardcode model_ids:[] — that bypasses the user's "
        "Creator-page model selection"
    )


def test_frontend_shows_per_file_model_badge():
    """File tree must show the generated_by badge so user can see
    which model wrote each file (their question:
    'امضاشون پای کار ثبت می‌شه؟')."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "generated_by" in src, (
        "frontend must use the generated_by field from the project "
        "files response to render a model badge"
    )


def test_frontend_audit_modal_shows_models_consulted():
    """The audit modal should display which models did the audit so
    the user can verify their selection was honored end-to-end."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "model_ids_used" in src
    assert "audit توسط" in src or "audit توسط:" in src or "موتور خالق" in src


# ─────────────────────────────────────────────────────────────────────────────
# "Do everything" button + button isolation
# ─────────────────────────────────────────────────────────────────────────────


def test_frontend_has_apply_all_recommended_button():
    """The user explicitly asked which button does EVERYTHING. The modal
    must have an unambiguous 'apply all' option that combines:
    promote (if needed) + add missing + modify selected + delete selected.
    Without this, user has to chain multiple buttons → easy to forget
    one, or click the wrong button and skip something."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    # Recommended-button visual marker
    assert "توصیه شده" in src and "اعمال کامل" in src, (
        "the recommended 'apply all' button must be present with a "
        "clear Persian label so the user immediately knows which "
        "button does the complete fix"
    )
    # Source: it must pass all four intent flags so the backend
    # doesn't silently drop one
    idx = src.find("توصیه شده")
    body = src[idx:idx + 3000]
    assert "includeMissing: true" in body
    assert "includeModifies: true" in body
    assert "includeDeletes: true" in body


def test_frontend_granular_buttons_use_positive_flags():
    """🚨 Old design used negative flags (onlyMissing, upgradeOnly).
    The bug: 'فقط حذف' button still sent missing_files because the
    inclusion condition was `!upgradeOnly && missing_critical_files`.
    The fix switched to positive `include*` flags so each intent is
    explicit. This test guards against regression."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    # The old negative flags must not be USED as opts (comments are fine
    # since they explain the migration). Specifically: no button passes
    # `onlyMissing: true` or `upgradeOnly: true` anymore.
    assert "onlyMissing: true" not in src, (
        "no button should pass `onlyMissing: true` — that was the "
        "negative-flag form that caused 'فقط حذف' to accidentally also "
        "send missing_files. Use positive includeMissing."
    )
    assert "upgradeOnly: true" not in src, (
        "upgradeOnly: true is gone — superseded by explicit includeMissing"
    )
    # Positive flags are present
    assert "includeMissing" in src
    assert "includeModifies" in src
    assert "includeDeletes" in src


def test_frontend_promote_button_now_also_sends_missing_files():
    """🐛 Original 🚀 promote button used `else if` so missing_files
    was NEVER sent alongside upgrade. Audit-specific paths (the 18
    files the AI flagged for THIS project) were silently dropped —
    only the generic fullstack template was applied. The recommended
    button now passes both upgrade AND missing_files independently."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    # The recommended button's options must include BOTH
    idx = src.find("توصیه شده")
    body = src[idx:idx + 3000]
    assert "upgradeFullstack:" in body and "includeMissing: true" in body, (
        "recommended button must send upgrade_to_fullstack AND "
        "missing_files together so audit-specific paths aren't dropped"
    )


@pytest.mark.asyncio
async def test_apply_fixes_handles_upgrade_plus_missing_plus_modify_plus_delete(tmp_path):
    """🚨 End-to-end: when the recommended button sends ALL four intents,
    the backend must execute all of them in correct order:
      1. delete listed files (gone from disk + project.files)
      2. modify selected files (regenerated with audit context)
      3. add audit's missing files (generated) AND fullstack template
         files (deduplicated)
      4. project.project_type updates to fullstack
    This is the most complex code path and the user's expected
    behavior. Without this test, a regression could silently skip
    one of the four."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest, FileToModify,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_all_in_one_999",
        name="AllInOneTest",
        description="full e2e CRUD audit-fix test",
        project_type="fastapi",
        files=[
            ProjectFile(
                path="backend/app/main.py", content="# bad", language="python",
            ),
            ProjectFile(
                path="backend/legacy.py", content="# to delete", language="python",
            ),
        ],
    )
    creator.projects[proj.id] = proj
    proj_dir = tmp_path / proj.id
    (proj_dir / "backend/app").mkdir(parents=True, exist_ok=True)
    (proj_dir / "backend/app/main.py").write_text("# bad")
    (proj_dir / "backend/legacy.py").write_text("# to delete")

    async def fake_legacy(prompt, model_ids=None):
        return "// new"

    async def fake_with_meta(prompt, model_ids=None):
        return ("// new content", "fake-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate", new=fake_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta",
        new=fake_with_meta,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                upgrade_to_fullstack=True,
                missing_files=["frontend/src/app/dashboard.tsx"],
                files_to_modify=[
                    FileToModify(
                        path="backend/app/main.py",
                        issue="needs routes",
                        suggestion="add include_router",
                    ),
                ],
                files_to_delete=["backend/legacy.py"],
            ),
        )

    # 1. Delete worked
    deleted = [f["path"] for f in result["files_deleted"]]
    assert "backend/legacy.py" in deleted
    assert not (proj_dir / "backend/legacy.py").exists()

    # 2. Modify worked
    modified = [f["path"] for f in result["files_modified"]]
    assert "backend/app/main.py" in modified
    main_py = next(f for f in proj.files if f.path == "backend/app/main.py")
    assert main_py.content == "// new content"

    # 3. Add — both audit's specific file AND fullstack template
    added = [f["path"] for f in result["files_added"]]
    assert "frontend/src/app/dashboard.tsx" in added, (
        "audit-specific missing file must be added (the regression "
        "where 🚀 button dropped them)"
    )
    # Template files too (e.g., frontend/src/app/page.tsx is in the
    # fullstack template)
    assert "frontend/src/app/page.tsx" in added

    # 4. Promotion landed
    assert result["promoted_to_fullstack"] is True
    assert proj.project_type == "fullstack"


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end persistence — does each button save state correctly so a
# page reload shows the new state? User's question:
#   "بدون باگ و بدون هیچ خطایی تمام کار لازم رو انجام میدم؟
#    درست ذخیره میکنن؟"
# These tests load the project from disk after apply-fixes and verify.
# ─────────────────────────────────────────────────────────────────────────────


def _reload_project_from_disk(workspace, project_id):
    """Spin up a fresh SimpleProjectCreator instance pointed at the
    same workspace — this is what the backend does on cold restart
    or when the singleton is cleared. If our metadata persistence is
    broken, the reloaded project will be missing the changes."""
    from app.services.simple_creator import SimpleProjectCreator
    fresh = SimpleProjectCreator(workspace=str(workspace))
    return fresh.get_project(project_id)


@pytest.mark.asyncio
async def test_e2e_add_only_button_persists(tmp_path):
    """⭐ 📄 'فقط افزودن' button — generates missing files AND saves
    the project meta so the additions survive a backend restart."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_e2e_add_001",
        name="AddE2E",
        description="add-only persistence",
        project_type="fastapi",
        files=[ProjectFile(path="backend/main.py", content="# old")],
    )
    creator.projects[proj.id] = proj
    (tmp_path / proj.id / "backend").mkdir(parents=True, exist_ok=True)
    (tmp_path / proj.id / "backend/main.py").write_text("# old")

    async def f_legacy(p, model_ids=None): return "// new"
    async def f_meta(p, model_ids=None): return ("// new", "test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate", new=f_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=f_meta,
    ):
        result = await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(missing_files=["frontend/page.tsx"]),
        )

    assert result["success"]
    assert (tmp_path / proj.id / "frontend/page.tsx").exists()

    # Reload from disk — the meta file MUST list the new file
    reloaded = _reload_project_from_disk(tmp_path, proj.id)
    assert reloaded is not None
    paths = [f.path for f in reloaded.files]
    assert "frontend/page.tsx" in paths, (
        "frontend/page.tsx was generated on disk but the project meta "
        "(project.json) wasn't updated — reload shows it missing. "
        "User would lose the addition after backend restart."
    )


@pytest.mark.asyncio
async def test_e2e_modify_only_button_persists(tmp_path):
    """✏️ 'فقط ویرایش' button — overwrites the file content AND saves
    meta so reload shows the new content."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest, FileToModify,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_e2e_mod_002",
        name="ModE2E",
        description="modify persistence",
        project_type="fastapi",
        files=[ProjectFile(path="main.py", content="OLD_CONTENT")],
    )
    creator.projects[proj.id] = proj
    (tmp_path / proj.id).mkdir(parents=True, exist_ok=True)
    (tmp_path / proj.id / "main.py").write_text("OLD_CONTENT")

    async def f_legacy(p, model_ids=None): return "NEW_CONTENT"
    async def f_meta(p, model_ids=None): return ("NEW_CONTENT", "test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate", new=f_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=f_meta,
    ):
        await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                files_to_modify=[
                    FileToModify(path="main.py", issue="x", suggestion="y"),
                ],
            ),
        )

    # Disk must have the new content
    assert (tmp_path / proj.id / "main.py").read_text() == "NEW_CONTENT"

    # Reload from disk: project.json must reflect new content
    reloaded = _reload_project_from_disk(tmp_path, proj.id)
    main = next((f for f in reloaded.files if f.path == "main.py"), None)
    assert main is not None
    assert main.content == "NEW_CONTENT", (
        "modify updated the file on disk but project.json still has the "
        "old content — reload would show stale state"
    )


@pytest.mark.asyncio
async def test_e2e_delete_only_button_persists(tmp_path):
    """🗑 'فقط حذف' button — removes file from disk AND from project
    meta so reload doesn't resurrect the deleted entry."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_e2e_del_003",
        name="DelE2E",
        description="delete persistence",
        project_type="fastapi",
        files=[
            ProjectFile(path="keep.py", content="# keep"),
            ProjectFile(path="remove.py", content="# remove"),
        ],
    )
    creator.projects[proj.id] = proj
    proj_dir = tmp_path / proj.id
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "keep.py").write_text("# keep")
    (proj_dir / "remove.py").write_text("# remove")

    await apply_audit_fixes(
        proj.id,
        ApplyAuditFixesRequest(files_to_delete=["remove.py"]),
    )

    # Disk: remove.py is gone, keep.py is intact
    assert not (proj_dir / "remove.py").exists()
    assert (proj_dir / "keep.py").exists()

    # Reload from disk: project.json must NOT contain remove.py
    reloaded = _reload_project_from_disk(tmp_path, proj.id)
    paths = [f.path for f in reloaded.files]
    assert "remove.py" not in paths, (
        "deleted file is gone from disk but still appears in project.json "
        "— after reload the file tree would show a 'phantom' entry"
    )
    assert "keep.py" in paths


@pytest.mark.asyncio
async def test_e2e_promote_only_button_persists(tmp_path):
    """🚀 'فقط ارتقا' button — updates project_type AND structure metadata
    so reload shows the new type."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_e2e_promote_004",
        name="PromoteE2E",
        description="promote persistence",
        project_type="fastapi",
    )
    creator.projects[proj.id] = proj
    (tmp_path / proj.id).mkdir(parents=True, exist_ok=True)

    async def f_legacy(p, model_ids=None): return "// generated"
    async def f_meta(p, model_ids=None): return ("// generated", "test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate", new=f_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=f_meta,
    ):
        await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(upgrade_to_fullstack=True),
        )

    # Reload: project_type must persist as fullstack
    reloaded = _reload_project_from_disk(tmp_path, proj.id)
    assert reloaded.project_type == "fullstack", (
        "promote updated project_type in memory but project.json still "
        "says 'fastapi' — reload reverts the promotion"
    )


@pytest.mark.asyncio
async def test_e2e_recommended_button_persists_all_four_intents(tmp_path):
    """⭐ The recommended 'اعمال کامل' button — runs all four ops in one
    POST. After it returns, a fresh load from disk MUST show every
    change persisted. This is the test that proves the recommended
    button actually does what its label promises."""
    from app.api.routes.simple_projects import (
        apply_audit_fixes, ApplyAuditFixesRequest, FileToModify,
    )
    from app.services.simple_creator import (
        get_simple_creator, Project, ProjectFile,
    )

    creator = get_simple_creator()
    creator.workspace = tmp_path
    proj = Project(
        id="proj_e2e_recommended_005",
        name="RecommendedE2E",
        description="full CRUD persistence",
        project_type="fastapi",
        files=[
            ProjectFile(path="backend/main.py", content="STUB"),
            ProjectFile(path="backend/legacy.py", content="REMOVE_ME"),
        ],
    )
    creator.projects[proj.id] = proj
    proj_dir = tmp_path / proj.id
    (proj_dir / "backend").mkdir(parents=True, exist_ok=True)
    (proj_dir / "backend/main.py").write_text("STUB")
    (proj_dir / "backend/legacy.py").write_text("REMOVE_ME")

    async def f_legacy(p, model_ids=None): return "REGENERATED"
    async def f_meta(p, model_ids=None): return ("REGENERATED", "test-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate", new=f_legacy,
    ), patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=f_meta,
    ):
        await apply_audit_fixes(
            proj.id,
            ApplyAuditFixesRequest(
                upgrade_to_fullstack=True,
                missing_files=["frontend/src/app/dashboard.tsx"],
                files_to_modify=[
                    FileToModify(
                        path="backend/main.py",
                        issue="needs routes",
                        suggestion="add include_router",
                    ),
                ],
                files_to_delete=["backend/legacy.py"],
            ),
        )

    # Reload from cold: every change must be there
    reloaded = _reload_project_from_disk(tmp_path, proj.id)
    assert reloaded is not None

    # 1. Project type promoted
    assert reloaded.project_type == "fullstack"

    # 2. Delete persisted
    paths = [f.path for f in reloaded.files]
    assert "backend/legacy.py" not in paths

    # 3. Modify persisted (new content)
    mod = next((f for f in reloaded.files if f.path == "backend/main.py"), None)
    assert mod is not None
    assert mod.content == "REGENERATED", (
        "modify updated the file on disk but project.json didn't get "
        "the new content — reload shows stale STUB"
    )

    # 4. Audit-specific missing file added
    assert "frontend/src/app/dashboard.tsx" in paths, (
        "the audit-specific missing file was generated on disk but "
        "isn't in project.json after reload"
    )

    # 5. Fullstack template files added too
    assert "frontend/src/app/page.tsx" in paths, (
        "fullstack template files weren't persisted in project.json"
    )

    # 6. generated_by attribution survives reload
    page = next((f for f in reloaded.files if f.path == "frontend/src/app/page.tsx"), None)
    assert page is not None
    assert page.generated_by == "test-model", (
        "model attribution must survive the disk roundtrip — without "
        "this the UI badge would be blank after restart"
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


# ─────────────────────────────────────────────────────────────────────────────
# 🆕 Audit history + regression detection + larger file/char caps
# (User reported: scores going DOWN after apply, no model picker on this page)
# ─────────────────────────────────────────────────────────────────────────────


def test_project_dataclass_has_audit_history_field():
    """Project must persist audit_history so the next audit can detect
    regression and the UI can show trend."""
    from app.services.simple_creator import Project
    p = Project(id="x", name="x", description="x", project_type="api")
    assert hasattr(p, "audit_history")
    assert p.audit_history == []
    d = p.to_dict()
    assert "audit_history" in d


def test_audit_prompt_widens_file_and_char_caps():
    """The 80-files × 800-chars cap from the original audit was too
    aggressive: re-audits would see only the prefix of every file, so
    even after regen the same 'stub detected' issue kept firing.
    Caps walked back from 200×4000 → 100×2000 after the streaming-
    timeout fix: huge prompts made Claude opus stream a response for
    60+ seconds that hit the max_tokens cap mid-JSON. Current caps
    (100×2000 = ~200KB) are still 2.5× the original 80×800 visibility
    while staying under model output budgets."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    body = src[idx:idx + 14000]
    assert "MAX_FILES = 100" in body, (
        "audit must scan up to 100 files — well above the 80 original"
    )
    assert "MAX_CHARS_PER_FILE = 2000" in body, (
        "audit must show up to 2000 chars per file (2.5× the original "
        "800, but small enough that opus responds without truncating)"
    )
    assert "TRUNCATED" in body, (
        "truncated files must be marked so the model doesn't infer "
        "'missing content' from a prefix-only view"
    )


def test_audit_prompt_includes_previous_audit_context():
    """When project.audit_history has prior events, the prompt must
    include them so the model can verify what was supposed to be fixed
    and avoid hallucinating regression. Without this, every audit is
    independent and scores oscillate as different models disagree."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    body = src[idx:idx + 14000]
    assert "previous_context" in body, (
        "audit must build a previous-audit context block"
    )
    assert "تاریخچهٔ audit" in body, (
        "the prompt must include the audit-history section in Persian"
    )
    assert "regression" in body, (
        "the prompt must instruct the model to flag regression explicitly"
    )


def test_audit_aggregated_exposes_regression_signals():
    """Frontend needs previous_score / score_delta / regression_warning
    so it can render the amber banner the user asked for."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    # Window widened to 24000 after convergence_notice block was added
    # between regression detection and history persistence.
    body = src[idx:idx + 24000]
    assert "regression_warning" in body
    assert "score_delta" in body
    assert "previous_score" in body


def test_audit_appends_to_history_and_persists():
    """After an audit run, the project's audit_history must gain a new
    'audit' event and the meta file must be saved. Without this, the
    history grows forgotten."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    # History append + meta-save live near the end of the function.
    # Widened to 25000 after convergence_notice block was added.
    body = src[idx:idx + 25000]
    assert "project.audit_history.append" in body
    # 20-entry cap so meta files stay small
    assert "audit_history[-20:]" in body
    # save_project_meta hook
    assert "_save_project_meta(project)" in body


def test_apply_fixes_appends_to_history():
    """apply-fixes must record an 'apply' event including the paths
    touched, so the next audit knows which files just changed."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def apply_audit_fixes")
    # The history append is well past the function entry; search the
    # remainder.
    body = src[idx:idx + 20000]
    assert "project.audit_history.append" in body
    assert '"kind": "apply"' in body
    assert '"applied_paths"' in body


def test_frontend_project_page_has_model_picker():
    """User explicitly asked for this:
    «وقتی روی یه پروژه ساخته شده کلیک میکنم، وقتی میخوام بررسی دوباره
     بزنم، جایی نیست که بتونم انتخاب کنم کدوم مدل کار انجام بده»
    The picker must (a) fetch from /api/simple/status, (b) render
    toggle chips, (c) write to localStorage 'creator_selected_models'
    so cross-page selection stays consistent."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "availableModels" in src and "auditModelIds" in src
    assert "/api/simple/status" in src
    assert "creator_selected_models" in src
    assert "toggleAuditModel" in src
    # Picker label in Persian so the user can find it
    assert "مدل‌های audit" in src or "مدل‌های audit / اصلاح" in src


def test_frontend_project_page_renders_regression_banner():
    """The amber regression banner is the visible signal the user
    asked for. Must read from aggregated.regression_warning."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "regression_warning" in src
    assert "هشدار regression" in src or "regression" in src


def test_frontend_project_page_renders_audit_history():
    """User should see the trend of past audit/apply events."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "audit_history" in src
    assert "تاریخچه" in src and ("audit" in src or "apply" in src)


def test_audit_exposes_convergence_notice():
    """User reported audit→apply→audit cycle with oscillating scores
    (58→62→58, modify count growing 15→16→19). When recent 3 audits
    show scores within ±5 and similar modify counts, backend must emit
    a convergence_notice so the frontend can show a green 'project is
    good enough — stop iterating' banner. Without this, the user is
    stuck in an infinite cycle."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    body = src[idx:idx + 25000]
    assert "convergence_notice" in body, (
        "audit must compute convergence_notice and expose it in "
        "aggregated so frontend can show 'project is done' banner"
    )
    assert "oscillation" in body.lower() or "همگرایی" in body, (
        "the convergence detection must be documented in code so future "
        "readers know what it solves"
    )


def test_audit_prompt_discourages_subjective_issues():
    """User explicitly asked: scores oscillate because every audit
    finds 'new' issues, but they're really just subjective opinions
    (could be more comprehensive / more idiomatic / nice to have).
    The prompt must include a 'do NOT flag' negative list to break
    the cycle."""
    src = (
        _BACKEND_ROOT / "app/api/routes/simple_projects.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def audit_project")
    body = src[idx:idx + 18000]
    # Persian negative-list markers — these are the patterns the user
    # complained about and must be explicitly forbidden in the prompt
    assert "بهتر باشد" in body or "می‌تواند" in body, (
        "prompt must list forbidden subjective categories ('could be "
        "better', 'might be more complete') to break the cycle"
    )
    # Must mention iterative loop awareness
    assert "حلقه" in body, (
        "prompt must tell the model it's in an iterative loop and that "
        "over-flagging traps the user"
    )


def test_frontend_renders_convergence_banner():
    """The green convergence banner is the visual signal the user
    needs to know 'project is done, push it'."""
    src = (
        _FRONTEND_ROOT / "app/project/[id]/page.tsx"
    ).read_text(encoding="utf-8")
    assert "convergence_notice" in src
    # Green styling (not red/amber) so the message reads as "all good"
    assert "bg-green-500" in src and "convergence_notice" in src


# ─────────────────────────────────────────────────────────────────────────────
# 🐛 Convergence threshold regression — user's actual screen scenario
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_convergence_fires_on_users_real_oscillation_pattern(monkeypatch, tmp_path):
    """🚨 First convergence implementation required `mod_range <= 5` too.
    But user's actual screen showed 15→13→16→19 (range 6) — the *textbook*
    oscillation case — and the notice didn't fire. This test pins the
    threshold to score-only so future tightening doesn't regress to that
    "notice never shows up" bug."""
    from app.api.routes.simple_projects import audit_project, AuditProjectRequest
    from app.services.simple_creator import get_simple_creator, Project, ProjectFile

    monkeypatch.setattr(get_simple_creator(), "workspace", tmp_path)
    creator = get_simple_creator()

    # Replay user's actual history
    proj = Project(
        id="proj_convergence_user_repro",
        name="Detective-1",
        description="OSINT platform with FastAPI + Next.js",
        project_type="fullstack",
        status="created",
        files=[
            ProjectFile(
                path="backend/app/main.py",
                content="from fastapi import FastAPI\napp = FastAPI()",
                language="python",
            ),
        ],
        structure={"directories": ["backend"]},
        audit_history=[
            {"kind": "audit", "run_at": "2026-06-06T10:07:19",
             "overall_score": 58, "modify_count": 15, "missing_count": 14},
            {"kind": "apply", "run_at": "2026-06-06T10:20:00",
             "applied_paths": ["a.py"]},
            {"kind": "audit", "run_at": "2026-06-06T10:23:13",
             "overall_score": 62, "modify_count": 13, "missing_count": 0},
            {"kind": "apply", "run_at": "2026-06-06T10:35:50",
             "applied_paths": ["b.py"]},
            {"kind": "audit", "run_at": "2026-06-06T10:38:07",
             "overall_score": 62, "modify_count": 16, "missing_count": 6},
            {"kind": "apply", "run_at": "2026-06-06T10:53:45",
             "applied_paths": ["c.py"]},
        ],
    )
    creator.projects[proj.id] = proj

    # Mock the AI to return a 58-score audit, modify_count won't matter
    # (no files_to_modify in the response), but score within range
    async def fake_ai_with_score_58(prompt, model_ids=None, **kwargs):
        return (
            '{"overall_score": 58, "ready_to_push": false, '
            '"missing_critical_files": [], "files_to_modify": [], '
            '"files_to_delete": [], "structural_issues": [], '
            '"quality_concerns": [], "matches_goal": true, '
            '"goal_mismatch_reasons": [], "suggestions_before_push": [], '
            '"summary": "still oscillating"}'
        )

    # Make our fake-model pass the "available models" gate by stubbing
    # the manager. Otherwise the endpoint 400s before reaching the
    # convergence path we're testing.
    from types import SimpleNamespace
    fake_model = SimpleNamespace(id="fake-model")
    with patch(
        "app.api.routes.simple_projects.ai_generate", new=fake_ai_with_score_58,
    ), patch(
        "app.services.ai_manager.AIManager.get_available_models",
        return_value=[fake_model],
    ):
        result = await audit_project(
            proj.id, AuditProjectRequest(model_ids=["fake-model"]),
        )

    agg = result["aggregated"]
    assert agg["overall_score_avg"] == 58
    assert agg["convergence_notice"], (
        "Convergence MUST fire on the user's reported oscillation "
        "(scores 58→62→62→58, applies between each). If this regresses, "
        "the user is back in the infinite loop they reported."
    )
    # The text must call it out as oscillation, not as a problem
    assert "همگرایی" in agg["convergence_notice"]
