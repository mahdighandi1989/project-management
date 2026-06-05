"""🧠 Knowledge Center — pins all 7 explicit user requirements + the
two phases of the voice-recorded request.

User's seven explicit requirements (from this session's message):
  1. می‌توانم انتخاب کنم توسط کدوم مدل فعال موجود کار انجام بشه
  2. می‌توانم چیزایی که اضافه شده رو حذف کنم
  3. در پروژه‌های حاضر این پوشه ایجاد بشه
  4. برای پروژه‌های آینده به محض تحت نظارت قرار گرفتن ایجاد بشه
  5. صفحه‌بندی، فهرست‌بندی، نمایش عالی، جستجو، سورت، فیلتر، صفحه‌بندی
  6. در هر پوشه یه دفترچهٔ راهنما باشه (format guide)
  7. وقتی فایلی از داخل پنل آپلود می‌کنم، در همون فرمت ذخیره بشه
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend/src"


# ─────────────────────────────────────────────────────────────────────────────
# Service exists + format guide is non-empty + contains AI instructions
# ─────────────────────────────────────────────────────────────────────────────


def test_service_module_exists():
    from app.services.knowledge_center_service import (
        KnowledgeCenterService, get_knowledge_center_service,
        EXPERIENCE_FORMAT_README,
    )
    svc = get_knowledge_center_service()
    assert isinstance(svc, KnowledgeCenterService)


def test_format_readme_contains_required_sections():
    """Req #6 — every experiences/ folder gets a README that:
      - Documents naming/frontmatter
      - Has explicit AI instructions for project-agnostic write-ups
      - Tells AI to merge not replace existing canonical topics
    Without these, the user's "any model can read and produce conformant
    files" guarantee breaks."""
    from app.services.knowledge_center_service import EXPERIENCE_FORMAT_README
    txt = EXPERIENCE_FORMAT_README
    # File naming
    assert "topic-slug" in txt or "kebab-case" in txt
    # Frontmatter requirements
    assert "topic_canonical" in txt
    assert "merged_from" in txt
    # AI directive: project-agnostic
    assert "project-agnostic" in txt or "بدون نام پروژه" in txt
    # AI directive: merge not replace
    assert "MERGE" in txt and "REPLACE" in txt
    # Required sections in the body
    for required in (
        "چالش", "راه‌حل", "Pitfalls", "How to Apply Elsewhere", "References",
    ):
        assert required in txt, (
            f"format README must mention '{required}' so AI models know the "
            "section layout"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Req #5 — list_entries supports search/sort/filter/pagination
# ─────────────────────────────────────────────────────────────────────────────


def test_list_entries_supports_pagination_search_sort_filter(tmp_path, monkeypatch):
    """The list_entries method MUST support all 4 controls. We seed a
    fake index and verify each filter narrows the result, search
    matches title+summary+tags, sort orders correctly, pagination
    slices the page."""
    import json
    from app.services import knowledge_center_service as kcs
    # Redirect index to tmp_path
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "knowledge_center.json")
    entries = [
        {
            "id": f"e{i}", "project_id": f"p{i % 3}",
            "project_full_name": f"owner/repo{i % 3}",
            "path": f"experiences/topic-{i}.md",
            "title": f"Topic {i} About Google OAuth" if i < 5 else f"Topic {i} About FastAPI",
            "topic_canonical": f"topic-{i}",
            "tags": ["auth", "google"] if i < 5 else ["fastapi"],
            "source_type": "manual" if i % 2 == 0 else "chat-import",
            "summary": f"summary {i}",
            "size_bytes": 1000 + i * 100,
            "created_at": f"2026-06-{(i % 28) + 1:02d}T00:00:00Z",
            "updated_at": f"2026-06-{(i % 28) + 1:02d}T01:00:00Z",
        }
        for i in range(15)
    ]
    (tmp_path / "knowledge_center.json").write_text(
        json.dumps({"version": 1, "entries": entries}),
        encoding="utf-8",
    )

    svc = kcs.KnowledgeCenterService()

    # Pagination
    res = svc.list_entries(page=1, per_page=5)
    assert len(res["items"]) == 5
    assert res["total"] == 15
    assert res["pages"] == 3

    # Page 2
    res2 = svc.list_entries(page=2, per_page=5)
    assert len(res2["items"]) == 5
    # No overlap
    ids1 = {x["id"] for x in res["items"]}
    ids2 = {x["id"] for x in res2["items"]}
    assert ids1.isdisjoint(ids2)

    # Search (case-insensitive across title)
    res = svc.list_entries(page=1, per_page=20, search="OAuth")
    assert all("oauth" in x["title"].lower() for x in res["items"])

    # Tag filter
    res = svc.list_entries(page=1, per_page=20, tag="fastapi")
    assert all("fastapi" in (x.get("tags") or []) for x in res["items"])

    # Source filter
    res = svc.list_entries(page=1, per_page=20, source_type="chat-import")
    assert all(x["source_type"] == "chat-import" for x in res["items"])

    # Sort by title asc — first item must be lex-smallest
    res = svc.list_entries(page=1, per_page=20, sort="title_asc")
    titles = [x["title"] for x in res["items"]]
    assert titles == sorted(titles)


def test_list_entries_returns_facets():
    """The facets (tags / sources / projects) are how the UI builds the
    filter dropdowns. Without them, user can't discover what's filterable."""
    from app.services.knowledge_center_service import get_knowledge_center_service
    svc = get_knowledge_center_service()
    res = svc.list_entries(page=1, per_page=1)
    assert "facets" in res
    assert "tags" in res["facets"]
    assert "sources" in res["facets"]
    assert "projects" in res["facets"]


# ─────────────────────────────────────────────────────────────────────────────
# Req #4 — future watched projects auto-create folder via oversight hook
# ─────────────────────────────────────────────────────────────────────────────


def test_oversight_add_watched_triggers_ensure_folder():
    """Source check — oversight_service.add_watched must schedule
    ensure_folder_for_project so future watched projects get the
    experiences/ folder immediately. Without this hook, the user has to
    manually trigger /bootstrap each time they add a project."""
    src = (
        _BACKEND_ROOT / "app/services/oversight_service.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def add_watched")
    assert idx != -1
    body = src[idx:idx + 5000]
    assert "ensure_folder_for_project" in body, (
        "add_watched must call kc.ensure_folder_for_project (or schedule it) "
        "so newly-watched projects get the experiences folder right away"
    )
    assert "knowledge_center_service" in body
    # Must be in a try/except so a failed scaffold doesn't break add_watched
    assert "Exception" in body and "ensure_folder_for_project" in body


# ─────────────────────────────────────────────────────────────────────────────
# Req #3 — bootstrap_existing walks every currently-watched project
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bootstrap_existing_iterates_all_watched():
    """The /bootstrap endpoint walks the current watched list and calls
    ensure_folder on each. Idempotent — already-present folders are
    skipped without churning commits."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    from types import SimpleNamespace

    svc = KnowledgeCenterService()

    calls = []

    async def fake_ensure(project_id, project_full_name, github_token=None):
        calls.append((project_id, project_full_name))
        return {"created": True, "repo": project_full_name}

    fake_watched = [
        SimpleNamespace(id="w1", repo_full_name="owner/repo1"),
        SimpleNamespace(id="w2", repo_full_name="owner/repo2"),
        SimpleNamespace(id="w3", repo_full_name="owner/repo3"),
    ]
    fake_osv = SimpleNamespace(watched=fake_watched)

    with patch(
        "app.services.oversight_service.get_oversight_service",
        return_value=fake_osv,
    ), patch(
        "app.services.oversight_service.get_github_token",
        return_value="ghp_test",
    ), patch.object(svc, "ensure_folder_for_project", new=fake_ensure):
        result = await svc.bootstrap_existing()

    assert result["total"] == 3
    assert result["created"] == 3
    assert {c[1] for c in calls} == {"owner/repo1", "owner/repo2", "owner/repo3"}


@pytest.mark.asyncio
async def test_ensure_folder_is_idempotent_when_readme_exists():
    """If README already exists, ensure_folder must NOT call
    create_or_update_file again — otherwise every backend restart
    churns the repo with no-op commits."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()

    with patch.object(svc, "_gh_file_exists", AsyncMock(return_value=True)), \
         patch("app.services.github_pr_service.get_github_pr_service") as mp:
        result = await svc.ensure_folder_for_project(
            project_id="w1", project_full_name="owner/repo",
            github_token="ghp_x",
        )
        # Must NOT have called the PR service at all
        mp.return_value.create_or_update_file.assert_not_called()

    assert result["created"] is False
    assert result["reason"] == "already_exists"


# ─────────────────────────────────────────────────────────────────────────────
# Req #2 — delete entries
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_entry_removes_from_index_and_optionally_repo(
    tmp_path, monkeypatch,
):
    """delete_entry must remove the entry from the index. If
    delete_from_repo=True, also delete from the GitHub repo. If False,
    keep file but de-index."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "knowledge_center.json")
    entries = [
        {"id": "e1", "project_full_name": "owner/repo",
         "path": "experiences/x.md", "title": "x"},
        {"id": "e2", "project_full_name": "owner/repo",
         "path": "experiences/y.md", "title": "y"},
    ]
    (tmp_path / "knowledge_center.json").write_text(
        json.dumps({"version": 1, "entries": entries}),
        encoding="utf-8",
    )

    svc = kcs.KnowledgeCenterService()

    # First: delete_from_repo=False → de-index only
    with patch(
        "app.services.oversight_service.get_github_token", return_value="ghp_x",
    ):
        r = await svc.delete_entry("e1", delete_from_repo=False)
    assert r["ok"] is True
    assert r["deindexed"] is True
    assert r["repo_deleted"] is False
    # Index now has 1 entry
    listing = svc.list_entries(page=1, per_page=20)
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == "e2"

    # Second: delete_from_repo=True → also pr.delete_file called
    delete_called = {"n": 0}
    async def fake_delete(**kw):
        delete_called["n"] += 1
        return {"ok": True}

    class _FakePR:
        delete_file = staticmethod(fake_delete)

    with patch(
        "app.services.github_pr_service.get_github_pr_service",
        return_value=_FakePR(),
    ), patch(
        "app.services.oversight_service.get_github_token",
        return_value="ghp_x",
    ):
        r = await svc.delete_entry("e2", delete_from_repo=True)
    assert r["repo_deleted"] is True
    assert delete_called["n"] == 1


@pytest.mark.asyncio
async def test_delete_entry_404_on_unknown():
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()
    r = await svc.delete_entry("nonexistent_id")
    assert r["ok"] is False
    assert r["error"] == "entry_not_found"


# ─────────────────────────────────────────────────────────────────────────────
# Req #1 + #7 — import_chat_file accepts model_ids + multiple formats
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_chat_file_honors_model_ids(tmp_path, monkeypatch):
    """When the user picks specific models in the upload UI, those exact
    model_ids must be passed to ai_generate_with_meta. Without this, the
    upload feature ignores user choice (the same bug we fixed for the
    /creator audit flow in earlier commits)."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({"version": 1, "entries": []}), encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    captured = []

    async def fake_ai(prompt, model_ids=None):
        captured.append({"model_ids": list(model_ids or [])})
        return (
            '{"experiences": [{"title": "GoogleOAuth", '
            '"topic_canonical": "google-oauth", "tags": ["auth"], '
            '"challenge": "x", "solution": "y", "code_examples": "", '
            '"pitfalls": "", "apply_elsewhere": "", "confidence": 0.9}]}',
            "test-model-claude",
        )

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat.txt",
            content_bytes=b"This is a long chat export. " * 30,
            target_project_id=None,
            target_project_full_name=None,
            model_ids=["claude-sonnet-4-6", "gemini-2.5-flash"],
        )

    assert result["ok"] is True
    assert result["created"] >= 1
    # Every AI call must have honored the user's model_ids
    assert all(
        c["model_ids"] == ["claude-sonnet-4-6", "gemini-2.5-flash"]
        for c in captured
    )


@pytest.mark.asyncio
async def test_import_chat_file_attributes_extracted_entry_to_model(
    tmp_path, monkeypatch,
):
    """Created entry must have generated_by set to the model that
    actually responded. This is the same per-file attribution guarantee
    the /creator engine has."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({"version": 1, "entries": []}), encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    async def fake_ai(prompt, model_ids=None):
        return (
            '{"experiences": [{"title": "T", "topic_canonical": "t-canon", '
            '"tags": [], "challenge": "x", "solution": "y", '
            '"code_examples": "", "pitfalls": "", "apply_elsewhere": ""}]}',
            "specific-test-model-id",
        )

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat.md",
            content_bytes=b"some chat content that is long enough to pass the 50-char minimum filter for the import endpoint",
            target_project_id=None,
            target_project_full_name=None,
            model_ids=None,
        )

    created = result["created_entries"]
    assert len(created) >= 1
    assert created[0]["generated_by"] == "specific-test-model-id"


@pytest.mark.asyncio
async def test_import_chat_file_merges_existing_canonical_topic(
    tmp_path, monkeypatch,
):
    """Req #14 from voice notes: if the topic_canonical already exists,
    merge (don't add duplicate). Important so re-importing similar chats
    doesn't bloat the catalog with duplicates."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    # Pre-seed an entry with topic "google-oauth"
    (tmp_path / "kc.json").write_text(
        json.dumps({
            "version": 1,
            "entries": [
                {
                    "id": "existing-e1",
                    "project_full_name": "",
                    "path": "experiences/google-oauth.md",
                    "title": "Google OAuth",
                    "topic_canonical": "google-oauth",
                    "tags": ["auth"],
                    "source_type": "manual",
                    "merged_from": [],
                },
            ],
        }),
        encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    async def fake_ai(prompt, model_ids=None):
        return (
            '{"experiences": [{"title": "Google OAuth v2", '
            '"topic_canonical": "google-oauth", "tags": ["auth"], '
            '"challenge": "newer perspective", "solution": "additional steps", '
            '"code_examples": "", "pitfalls": "edge case found", '
            '"apply_elsewhere": ""}]}',
            "test-model",
        )

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat2.txt",
            content_bytes=b"existing topic chat with enough length to pass the 50-character minimum threshold check",
            target_project_id=None,
            target_project_full_name=None,
        )

    assert result["created"] == 0, "duplicate canonical must NOT create new"
    assert result["merged"] >= 1, "must MERGE into existing entry"
    # Existing entry now has merged_from populated
    listing = svc.list_entries(page=1, per_page=20)
    assert listing["total"] == 1
    existing = listing["items"][0]
    assert any("chat2.txt" in m for m in existing.get("merged_from", []))


# ─────────────────────────────────────────────────────────────────────────────
# Frontend page exists with all the required UI elements
# ─────────────────────────────────────────────────────────────────────────────


def test_frontend_page_exists():
    p = _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    assert p.exists(), "Knowledge Center page must exist at this path"


def test_sidebar_has_knowledge_center_entry():
    src = (
        _FRONTEND_ROOT / "components/Layout.tsx"
    ).read_text(encoding="utf-8")
    assert "/knowledge-center" in src
    assert "مرکز دانش" in src


def test_dashboard_has_knowledge_center_card():
    """Req: 'و همینطور توی داشبورد اصلی' — the home page must surface
    a card linking to Knowledge Center."""
    src = (_FRONTEND_ROOT / "app/page.tsx").read_text(encoding="utf-8")
    assert "/knowledge-center" in src
    assert "مرکز دانش" in src


def test_frontend_page_has_search_sort_filter_pagination():
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    # Search
    assert "جستجو" in src or "search" in src.lower()
    # Sort
    assert "sort" in src.lower() and "updated_desc" in src
    # Filter
    assert "tagFilter" in src and "projectFilter" in src
    # Pagination
    assert "per_page" in src or "perPage" in src
    assert "data.pages" in src or "result.pages" in src


def test_frontend_page_has_upload_modal_with_model_selection():
    """Req #1 + #7 — upload must let user pick which models do the
    extraction. Without this the chat-import bypasses the user's
    selection."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    assert "UploadChatModal" in src or "آپلود چت" in src
    # Model picker
    assert "selectedModels" in src or "selectedModelIds" in src
    # File accepts multiple formats (req #7)
    assert ".txt" in src and ".md" in src and ".pdf" in src
    # POSTs to /import endpoint
    assert "/knowledge-center/import" in src


def test_frontend_page_has_delete_button():
    """Req #2 — every entry has a delete button."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    assert "deleteEntry" in src
    assert "🗑" in src


def test_frontend_page_has_bootstrap_button():
    """Req #3 — UI exposes a way to retroactively create folders in
    every existing watched project."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    assert "/knowledge-center/bootstrap" in src
    assert "ساخت پوشهٔ تجربیات" in src or "bootstrap" in src.lower()
