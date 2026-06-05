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


# ─────────────────────────────────────────────────────────────────────────────
# Auto-sync + AI cross-repo processor (the user's follow-up questions)
# ─────────────────────────────────────────────────────────────────────────────


def test_settings_load_returns_defaults_when_file_absent(tmp_path, monkeypatch):
    """Defaults must be returned when the settings file doesn't exist
    yet (fresh deploy)."""
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")
    settings = kcs.load_settings()
    assert settings["auto_sync_enabled"] is True
    assert settings["auto_sync_interval_minutes"] == 60
    assert settings["skip_unchanged"] is True
    assert isinstance(settings.get("processing_model_ids"), list)


def test_settings_save_only_persists_known_keys(tmp_path, monkeypatch):
    """save_settings must reject unknown keys so a typo (e.g., 'enabled')
    doesn't shadow a real setting."""
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")
    res = kcs.save_settings({
        "auto_sync_enabled": False,
        "processing_model_ids": ["claude-x", "gemini-y"],
        "unknown_typo": "should_be_ignored",
    })
    assert res["auto_sync_enabled"] is False
    assert res["processing_model_ids"] == ["claude-x", "gemini-y"]
    assert "unknown_typo" not in res
    # Re-load preserves the saved values
    loaded = kcs.load_settings()
    assert loaded["auto_sync_enabled"] is False
    assert loaded["processing_model_ids"] == ["claude-x", "gemini-y"]


@pytest.mark.asyncio
async def test_process_skips_unchanged_entries(tmp_path, monkeypatch):
    """🚨 User's "بک اند سنگین نشه" requirement — entries whose
    content_hash matches last_processed_hash must NOT trigger AI calls.
    Without this, every autosync cycle re-pays the AI cost for every
    file regardless of whether it changed."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")

    # Seed entries: e1 unchanged (hash == last_processed), e2 changed
    (tmp_path / "kc.json").write_text(
        json.dumps({
            "version": 1,
            "entries": [
                {
                    "id": "e1", "project_full_name": "owner/repo1",
                    "path": "experiences/x.md", "title": "X",
                    "topic_canonical": "x", "tags": [], "summary": "old",
                    "content_hash": "h1", "last_processed_hash": "h1",
                },
                {
                    "id": "e2", "project_full_name": "owner/repo1",
                    "path": "experiences/y.md", "title": "Y",
                    "topic_canonical": "y", "tags": [], "summary": "old",
                    "content_hash": "h2", "last_processed_hash": "h-old",
                },
            ],
        }),
        encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    ai_call_count = {"n": 0, "ids": []}

    async def fake_ai(prompt, model_ids=None):
        ai_call_count["n"] += 1
        # Detect which entry was processed by searching the prompt
        if "X" in prompt:
            ai_call_count["ids"].append("e1")
        elif "Y" in prompt:
            ai_call_count["ids"].append("e2")
        return ("new summary", "fake-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ):
        result = await svc.process_synced_entries()

    assert result["processed"] == 1, "only e2 (changed) should be processed"
    assert result["skipped"] == 1, "e1 (unchanged) must be skipped"
    assert ai_call_count["n"] == 1, (
        "AI must be called exactly once — e1 must NOT trigger an AI call"
    )
    assert "e2" in ai_call_count["ids"]
    assert "e1" not in ai_call_count["ids"]


@pytest.mark.asyncio
async def test_process_with_force_ignores_skip_unchanged(tmp_path, monkeypatch):
    """force=True must re-process even unchanged entries (debugging /
    rebuild after prompt change)."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({
            "version": 1,
            "entries": [{
                "id": "e1", "project_full_name": "owner/repo",
                "path": "experiences/x.md", "title": "X",
                "topic_canonical": "x", "content_hash": "h",
                "last_processed_hash": "h",  # same → would normally skip
            }],
        }),
        encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    called = {"n": 0}

    async def fake_ai(prompt, model_ids=None):
        called["n"] += 1
        return ("re-processed", "model")

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ):
        result = await svc.process_synced_entries(force=True)

    assert called["n"] == 1, "force=True must trigger AI even on unchanged hash"
    assert result["processed"] == 1


@pytest.mark.asyncio
async def test_process_computes_cross_references_across_projects(tmp_path, monkeypatch):
    """🔗 The user asked: 'اگر چند ریپو چند فایل تجربیات داشتن که در
    جاهایی شبیه هم بود چجوری ادغام انجام میشه؟'

    Answer: entries with the same topic_canonical in different projects
    are cross-referenced (NOT duplicated). Each entry's cross_references
    points at the others — single source of truth, full traceability."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({
            "version": 1,
            "entries": [
                {
                    "id": "e1", "project_full_name": "owner/repoA",
                    "path": "experiences/google-oauth.md", "title": "Google OAuth A",
                    "topic_canonical": "google-oauth", "content_hash": "h1",
                    "last_processed_hash": "h1",  # skip AI but still get cross-refs
                },
                {
                    "id": "e2", "project_full_name": "owner/repoB",
                    "path": "experiences/google-oauth.md", "title": "Google OAuth B",
                    "topic_canonical": "google-oauth", "content_hash": "h2",
                    "last_processed_hash": "h2",
                },
                {
                    "id": "e3", "project_full_name": "owner/repoC",
                    "path": "experiences/unrelated.md", "title": "Other",
                    "topic_canonical": "unrelated", "content_hash": "hx",
                    "last_processed_hash": "hx",
                },
            ],
        }),
        encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()
    result = await svc.process_synced_entries()
    assert result["ok"] is True

    # Reload index — e1 must reference e2 (same canonical, diff project)
    idx = kcs._load_index()
    e1 = next(e for e in idx["entries"] if e["id"] == "e1")
    e2 = next(e for e in idx["entries"] if e["id"] == "e2")
    e3 = next(e for e in idx["entries"] if e["id"] == "e3")

    assert any(
        cr.get("entry_id") == "e2" for cr in e1.get("cross_references", [])
    ), (
        "e1 must have a cross-reference to e2 (same topic_canonical, "
        "different project)"
    )
    assert any(
        cr.get("entry_id") == "e1" for cr in e2.get("cross_references", [])
    )
    # e3 has different canonical → no cross-references
    assert e3.get("cross_references") == []


@pytest.mark.asyncio
async def test_process_honors_settings_model_ids_when_none_passed(tmp_path, monkeypatch):
    """When the caller doesn't pass model_ids, the processor must use
    settings.processing_model_ids. This lets the user 'set once' which
    models do background processing — without rewiring every call."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    monkeypatch.setattr(kcs, "SETTINGS_FILE", tmp_path / "kc_settings.json")
    kcs.save_settings({"processing_model_ids": ["claude-from-settings"]})
    (tmp_path / "kc.json").write_text(
        json.dumps({
            "version": 1,
            "entries": [{
                "id": "e1", "project_full_name": "p/r", "path": "experiences/a.md",
                "title": "A", "topic_canonical": "a", "content_hash": "h",
                "last_processed_hash": "",  # never processed
            }],
        }),
        encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    captured = {"models": None}

    async def fake_ai(prompt, model_ids=None):
        captured["models"] = list(model_ids) if model_ids else None
        return ("ok", "claude-from-settings")

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ):
        await svc.process_synced_entries()

    assert captured["models"] == ["claude-from-settings"], (
        "processing_model_ids from settings must flow into the AI call "
        "when the caller didn't specify model_ids"
    )


def test_autosync_loop_function_exists_and_is_async():
    """The lifespan registers this function — it must exist + be
    async + accept a stop_event."""
    import inspect
    from app.services.knowledge_center_service import (
        knowledge_center_autosync_loop,
    )
    assert inspect.iscoroutinefunction(knowledge_center_autosync_loop)
    sig = inspect.signature(knowledge_center_autosync_loop)
    assert "stop_event" in sig.parameters


def test_lifespan_wires_autosync_loop():
    """main.py must register the autosync loop in lifespan startup AND
    set up shutdown teardown. Otherwise the loop runs only after the
    first manual trigger (defeating the purpose of auto-sync)."""
    src = (
        _BACKEND_ROOT / "app/main.py"
    ).read_text(encoding="utf-8")
    assert "knowledge_center_autosync_loop" in src
    # Startup
    assert "kc_autosync_task" in src
    assert "kc_autosync_stop" in src
    # Shutdown teardown — graceful cancel
    idx_stop = src.rfind("kc_autosync_stop")
    body = src[idx_stop:idx_stop + 500]
    assert "stop_evt.set()" in body or ".set()" in body


def test_autosync_has_minimum_interval_floor():
    """Safety floor: even if user sets interval to 0 or 1, we must not
    poll faster than the floor (5 min) — protects from accidental DDoS
    of GitHub API."""
    from app.services.knowledge_center_service import (
        _KC_AUTOSYNC_MIN_INTERVAL_MIN,
    )
    assert _KC_AUTOSYNC_MIN_INTERVAL_MIN >= 5


def test_process_endpoint_registered():
    """The /process route must be registered so the UI/scheduler can
    trigger AI re-processing manually."""
    src = (
        _BACKEND_ROOT / "app/api/routes/knowledge_center.py"
    ).read_text(encoding="utf-8")
    assert '@router.post("/process")' in src
    assert "process_synced_entries" in src


def test_settings_endpoints_registered():
    src = (
        _BACKEND_ROOT / "app/api/routes/knowledge_center.py"
    ).read_text(encoding="utf-8")
    assert '@router.get("/settings")' in src
    assert '@router.patch("/settings")' in src
    # PATCH must accept processing_model_ids (so the user can set the
    # background-sync model list)
    assert "processing_model_ids" in src


# ─────────────────────────────────────────────────────────────────────────────
# Frontend settings UI — model picker pulls from /api/simple/status
# (user explicitly demanded: "هر مدلی که از صفحه مدل ها فعال بود")
# ─────────────────────────────────────────────────────────────────────────────


def test_frontend_has_settings_modal_with_model_picker():
    """🚨 User asked: 'چرا مدل رو خودت هاردکد انتخاب کردی؟ قرار شد هر
    مدلی که از صفحه مدل ها فعال بود بتونم اگر خواستم انتخاب کنم'.
    The UI must (a) fetch active models from /api/simple/status — the
    same source the /creator page uses — (b) render each as a
    selectable chip, and (c) PATCH the choice to the backend."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    # Settings panel must exist
    assert "settingsOpen" in src and "تنظیمات" in src
    # Must fetch from the same status endpoint /creator uses
    assert "/api/simple/status" in src
    # Must render the active models as toggle chips (the same pattern
    # the upload modal uses)
    assert "processing_model_ids" in src
    # PATCH path on toggle
    assert (
        "/api/knowledge-center/settings" in src
        and "method: 'PATCH'" in src
    ), (
        "settings panel must PATCH to /api/knowledge-center/settings — "
        "otherwise the user's model choice is never persisted"
    )


def test_frontend_settings_loads_current_value_on_mount():
    """The settings modal must show the CURRENTLY saved processing
    model selection on open, not reset to empty. Otherwise the user
    has to re-select every time."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    # GET /settings on mount
    assert "fetch(`${API_BASE}/api/knowledge-center/settings`)" in src
    assert "setKcSettings" in src


def test_frontend_settings_has_auto_sync_controls():
    """The settings panel must expose auto_sync_enabled toggle and
    interval input so user can pause/resume auto-sync without
    redeploying."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    assert "auto_sync_enabled" in src
    assert "auto_sync_interval_minutes" in src
    assert "skip_unchanged" in src


def test_frontend_has_manual_process_button():
    """The user must be able to trigger AI processing manually (without
    waiting for the next auto-sync cycle). Useful right after upload
    or after changing the model selection."""
    src = (
        _FRONTEND_ROOT / "app/knowledge-center/page.tsx"
    ).read_text(encoding="utf-8")
    assert "triggerManualProcess" in src
    assert "/knowledge-center/process" in src
    assert "🧠 پردازش با AI" in src or "پردازش با AI" in src


# ─────────────────────────────────────────────────────────────────────────────
# 🆕 Two-pass extraction quality — covers the voice-recorded asks about
# topic separation, thread following, resolution detection, recurrence,
# and project-agnostic reusability.
# ─────────────────────────────────────────────────────────────────────────────


def test_outline_parser_handles_well_formed_json():
    """Pass-1 parser must extract topic list with all expected fields."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()
    out = svc._parse_topic_outline(
        '{"topics": [{"topic_canonical":"x","title":"X",'
        '"message_anchors":["a","b"],"resolution_signal":"solved",'
        '"recurrence_count":3,"value_score":7}]}'
    )
    assert len(out["topics"]) == 1
    t = out["topics"][0]
    assert t["topic_canonical"] == "x"
    assert t["resolution_signal"] == "solved"
    assert t["recurrence_count"] == 3
    assert t["value_score"] == 7


def test_outline_parser_handles_code_fences_and_prose():
    """Models sometimes wrap JSON in ```json fences or add prefix prose.
    Parser must still recover."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()
    resp = (
        "Sure! Here is the outline you asked for:\n\n"
        "```json\n"
        '{"topics": [{"topic_canonical":"y","title":"Y",'
        '"message_anchors":[],"resolution_signal":"open",'
        '"recurrence_count":1,"value_score":5}]}\n'
        "```\n\nLet me know if you need more."
    )
    out = svc._parse_topic_outline(resp)
    assert len(out["topics"]) == 1


def test_outline_parser_returns_empty_on_garbage():
    """No crash on non-JSON / empty / wrong shape."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()
    assert svc._parse_topic_outline("") == {"topics": []}
    assert svc._parse_topic_outline("not json at all") == {"topics": []}
    assert svc._parse_topic_outline('{"wrong": "shape"}') == {"topics": []}


def test_deep_response_parser_returns_none_for_null_reply():
    """Pass-2 model says 'this topic isn't worth keeping' → null. Parser
    must return None so we skip it instead of creating a junk entry."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()
    assert svc._parse_topic_deep_response("null") is None
    assert svc._parse_topic_deep_response("```json\nnull\n```") is None
    assert svc._parse_topic_deep_response("") is None


def test_deep_response_parser_extracts_resolution_fields():
    """The pass-2 schema added resolution_status / evidence / recurrence
    / user_confirmed. Parser must surface them so they reach the
    rendered markdown."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    svc = KnowledgeCenterService()
    obj = svc._parse_topic_deep_response(
        '{"title":"T","topic_canonical":"t","challenge":"c",'
        '"solution":"s","resolution_status":"solved",'
        '"resolution_evidence":"user said it works",'
        '"recurrence_count":2,"user_confirmed":true,"confidence":0.9}'
    )
    assert obj is not None
    assert obj["resolution_status"] == "solved"
    assert obj["user_confirmed"] is True
    assert obj["recurrence_count"] == 2


def test_render_experience_md_includes_resolution_section():
    """The user wants the saved file to record HOW we know the topic was
    solved. Render must include the resolution block + applies_when
    bullets so the next reader can judge applicability."""
    from app.services.knowledge_center_service import KnowledgeCenterService
    md = KnowledgeCenterService._render_experience_md(
        title="OAuth", canonical="oauth", item={
            "challenge": "c", "solution": "s",
            "resolution_status": "solved",
            "resolution_evidence": "user confirmed",
            "recurrence_count": 2, "user_confirmed": True,
            "applies_when": ["building login", "need 3rd-party auth"],
            "applies_when_not": ["internal-only tool"],
            "prerequisites": ["OAuth2 lib"],
        }, source_file="chat.txt", used_model="m1",
        created_at="2026-06-05T10:00:00Z",
    )
    assert "resolution_status: \"solved\"" in md
    assert "user_confirmed: true" in md
    assert "user confirmed" in md  # evidence
    assert "Applies when" in md
    assert "building login" in md
    assert "anti-pattern" in md.lower()
    assert "Prerequisites" in md
    assert "OAuth2 lib" in md


def test_format_readme_documents_resolution_workflow():
    """README is the AI contract. If it doesn't mention the resolution
    fields, any new model writing experiences will skip them."""
    from app.services.knowledge_center_service import EXPERIENCE_FORMAT_README
    assert "resolution_status" in EXPERIENCE_FORMAT_README
    assert "regressed" in EXPERIENCE_FORMAT_README
    assert "user_confirmed" in EXPERIENCE_FORMAT_README
    assert "Applies when" in EXPERIENCE_FORMAT_README
    assert "anti-pattern" in EXPERIENCE_FORMAT_README.lower()
    assert "interleaved" in EXPERIENCE_FORMAT_README.lower() or (
        "پراکنده" in EXPERIENCE_FORMAT_README
    )


@pytest.mark.asyncio
async def test_import_chat_uses_two_pass_when_outline_returns_topics(
    tmp_path, monkeypatch,
):
    """Two-pass extraction: pass-1 outline returns N topics → pass-2 runs
    once per topic. Verifies orchestration."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({"version": 1, "entries": []}), encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    call_log = []

    async def fake_ai(prompt, model_ids=None):
        # Outline prompt asks for value_score; deep prompt asks for
        # resolution_evidence. Use those as unambiguous markers.
        if "value_score" in prompt and "resolution_evidence" not in prompt:
            call_log.append("outline")
            return (
                '{"topics": ['
                '{"topic_canonical":"oauth-flow","title":"OAuth Flow",'
                '"message_anchors":["need login"],'
                '"resolution_signal":"solved","recurrence_count":1,"value_score":8},'
                '{"topic_canonical":"rate-limit","title":"Rate Limiting",'
                '"message_anchors":["429 errors"],'
                '"resolution_signal":"partial","recurrence_count":2,"value_score":6}'
                ']}',
                "outline-model",
            )
        call_log.append("deep")
        return (
            '{"title":"Result","topic_canonical":"new-canonical",'
            '"tags":[],"challenge":"x","solution":"y","code_examples":"",'
            '"pitfalls":"","apply_elsewhere":"",'
            '"applies_when":["a"],"applies_when_not":[],"prerequisites":[],'
            '"resolution_status":"solved","resolution_evidence":"works",'
            '"recurrence_count":1,"user_confirmed":true,"confidence":0.9}',
            "deep-model",
        )

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat.txt",
            content_bytes=b"long enough chat content " * 30,
            target_project_id=None, target_project_full_name=None,
        )

    assert result["ok"] is True
    assert result["pass_mode"] == "two_pass"
    assert result["topics_identified"] == 2
    assert call_log == ["outline", "deep", "deep"]
    assert result["created"] == 2


@pytest.mark.asyncio
async def test_import_chat_skips_low_value_topics(tmp_path, monkeypatch):
    """value_score < 4 → topic dropped before pass-2. Saves AI cost and
    keeps the catalog clean."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({"version": 1, "entries": []}), encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    deep_calls = {"n": 0}

    async def fake_ai(prompt, model_ids=None):
        if "value_score" in prompt and "resolution_evidence" not in prompt:
            return (
                '{"topics": ['
                '{"topic_canonical":"junk","title":"trivial",'
                '"message_anchors":[],"resolution_signal":"open",'
                '"recurrence_count":1,"value_score":2}'
                ']}',
                "outline-model",
            )
        deep_calls["n"] += 1
        return ('{"title":"x"}', "deep-model")

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat.txt",
            content_bytes=b"long enough chat content " * 30,
            target_project_id=None, target_project_full_name=None,
        )

    assert result["topics_identified"] == 1
    assert deep_calls["n"] == 0, "low-value topic must not trigger pass-2"
    assert result["created"] == 0


@pytest.mark.asyncio
async def test_import_chat_falls_back_to_chunking_when_outline_fails(
    tmp_path, monkeypatch,
):
    """If pass-1 errors, fall back to chunk + single-pass so we don't
    lose data."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({"version": 1, "entries": []}), encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    call_count = {"n": 0}

    async def fake_ai(prompt, model_ids=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("rate limited")
        return (
            '{"experiences": [{"title":"Fallback Topic",'
            '"topic_canonical":"fallback","tags":[],"challenge":"x",'
            '"solution":"y","code_examples":"","pitfalls":"",'
            '"apply_elsewhere":""}]}',
            "fallback-model",
        )

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat.txt",
            content_bytes=b"long enough chat content " * 30,
            target_project_id=None, target_project_full_name=None,
        )

    assert result["pass_mode"] == "single_pass_fallback"
    assert result["created"] >= 1
    assert any("outline pass" in e for e in result.get("errors", []))


@pytest.mark.asyncio
async def test_import_chat_two_pass_dedups_against_existing_canonical(
    tmp_path, monkeypatch,
):
    """Two-pass path must respect the same dedup contract as single-pass:
    matching canonical → merge, not duplicate."""
    import json
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    (tmp_path / "kc.json").write_text(
        json.dumps({"version": 1, "entries": [{
            "id": "e-existing", "project_full_name": "",
            "path": "experiences/oauth-flow.md", "title": "Old OAuth",
            "topic_canonical": "oauth-flow", "tags": [],
            "source_type": "manual", "merged_from": [],
        }]}),
        encoding="utf-8",
    )
    svc = kcs.KnowledgeCenterService()

    async def fake_ai(prompt, model_ids=None):
        if "value_score" in prompt and "resolution_evidence" not in prompt:
            return (
                '{"topics":[{"topic_canonical":"oauth-flow",'
                '"title":"OAuth","message_anchors":[],'
                '"resolution_signal":"solved","recurrence_count":1,'
                '"value_score":7}]}',
                "outline-model",
            )
        return (
            '{"title":"OAuth v2","topic_canonical":"oauth-flow",'
            '"tags":[],"challenge":"x","solution":"y",'
            '"code_examples":"","pitfalls":"","apply_elsewhere":""}',
            "deep-model",
        )

    with patch(
        "app.api.routes.simple_projects.ai_generate_with_meta", new=fake_ai,
    ), patch(
        "app.services.oversight_service.get_github_token", return_value=None,
    ):
        result = await svc.import_chat_file(
            filename="chat-dup.txt",
            content_bytes=b"long enough chat content " * 30,
            target_project_id=None, target_project_full_name=None,
        )

    assert result["created"] == 0
    assert result["merged"] >= 1
