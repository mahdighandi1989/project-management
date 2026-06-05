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
