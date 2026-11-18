"""PM-INS-0028 — Knowledge Center: background sync with progress, clickable tag
chips, and experiences that are actually USED (retrieval + usage log + «📚» line)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_ROOT = Path(__file__).resolve().parents[2]

PROXY_ENTRY = {
    "id": "px1", "project_id": "w1", "project_full_name": "owner/alpha",
    "path": "experiences/headless-chromium-behind-tls-proxy.md",
    "title": "Headless Chromium behind a TLS-inspecting egress proxy",
    "topic_canonical": "headless-chromium-behind-tls-proxy",
    "tags": ["playwright", "chromium", "proxy", "tls"],
    "summary": "Launching Playwright behind a proxy that re-signs TLS.",
    "updated_at": "2026-11-01T00:00:00Z", "created_at": "2026-11-01T00:00:00Z",
}
OTHER_ENTRY = {
    "id": "ga1", "project_id": "w2", "project_full_name": "owner/beta",
    "path": "experiences/google-oauth-login.md", "title": "Google OAuth login",
    "topic_canonical": "google-oauth-login", "tags": ["auth", "oauth"],
    "summary": "Login with Google.", "updated_at": "2026-10-01T00:00:00Z",
}


@pytest.fixture
def kc(tmp_path, monkeypatch):
    from app.services import knowledge_center_service as kcs
    monkeypatch.setattr(kcs, "INDEX_FILE", tmp_path / "kc.json")
    monkeypatch.setattr(kcs, "USAGE_FILE", tmp_path / "kc_usage.json")
    (tmp_path / "kc.json").write_text(json.dumps({"entries": [PROXY_ENTRY, OTHER_ENTRY]}), encoding="utf-8")
    return kcs


def test_persian_question_about_playwright_behind_proxy_finds_the_lesson(kc):
    hits = kc.find_relevant_entries("Playwright پشتِ پراکسی کار نمی‌کند، چه کنم؟")
    assert hits and hits[0]["id"] == "px1"
    assert all(h["id"] != "ga1" for h in hits)


def test_unrelated_question_injects_nothing(kc):
    assert kc.find_relevant_entries("سلام، حالت چطور است؟") == []


def test_experience_context_records_usage_and_list_shows_it(kc):
    with patch("app.services.oversight_service.get_github_token", return_value=""):
        out = asyncio.run(kc.experience_context("playwright behind proxy", "inspector", "owner/gamma"))
    assert "Headless Chromium behind a TLS-inspecting egress proxy" in out["line"]
    assert out["line"].startswith("📚 تجربه‌های به‌کاررفته")
    assert "Headless Chromium" in out["block"]
    u = kc.usage_for("px1")
    assert u["usage_count"] == 1 and u["last_used_where"] == "inspector" and u["last_used_project"] == "owner/gamma"
    listed = {x["id"]: x for x in kc.KnowledgeCenterService().list_entries(per_page=10)["items"]}
    assert listed["px1"]["usage_count"] == 1 and listed["ga1"]["usage_count"] == 0
    assert kc.KnowledgeCenterService().get_entry("px1")["usage_recent"][0]["where"] == "inspector"


def test_sync_skips_unchanged_blobs_counts_updates_and_persists_last_sync(kc):
    svc = kc.KnowledgeCenterService()
    watched = [SimpleNamespace(id="w1", repo_full_name="owner/alpha")]
    listing = [
        {"name": "headless-chromium-behind-tls-proxy.md", "path": PROXY_ENTRY["path"], "sha": "s1"},
        {"name": "new-one.md", "path": "experiences/new-one.md", "sha": "s2"},
    ]
    fetched = []

    async def fake_list(*a, **k):
        return listing

    async def fake_get(owner, repo, path, token):
        fetched.append(path)
        return f"---\ntitle: T {path}\ntags: [x]\n---\n\nbody {path}\n"

    osv = SimpleNamespace(watched=watched)
    with patch("app.services.oversight_service.get_oversight_service", return_value=osv), \
         patch("app.services.oversight_service.get_github_token", return_value="tok"), \
         patch.object(svc, "_gh_list_directory", fake_list), patch.object(svc, "_gh_get_file_content", fake_get):
        r1 = asyncio.run(svc.sync_from_projects())
        assert r1["added"] == 1 and r1["updated"] == 1  # the proxy entry had no sha and its body changed
        fetched.clear()
        r2 = asyncio.run(svc.sync_from_projects())
    assert fetched == []  # same blob shas ⇒ nothing re-downloaded
    assert r2["added"] == 0 and r2["updated"] == 0 and r2["unchanged"] == 2
    last = json.loads(kc.INDEX_FILE.read_text(encoding="utf-8"))["last_sync"]
    assert last["projects"][0]["repo"] == "owner/alpha" and last["at"]
    assert kc.sync_status()["last_sync"]["unchanged"] == 2


def test_sync_route_starts_background_job_and_status_route_exists():
    src = (_ROOT / "backend/app/api/routes/knowledge_center.py").read_text(encoding="utf-8")
    assert '@router.get("/sync/status")' in src and "start_sync_job" in src


def test_inspector_and_assistant_use_experiences():
    rl = (_ROOT / "backend/app/api/routes/render_logs.py").read_text(encoding="utf-8")
    assert 'experience_context as _kc_ctx' in rl and '_kc_state["line"]' in rl
    asst = (_ROOT / "backend/app/services/assistant.py").read_text(encoding="utf-8")
    assert 'experience_context(question, "assistant"' in asst


def test_frontend_tag_chips_filter_and_sync_shows_progress():
    page = (_ROOT / "frontend/src/app/knowledge-center/page.tsx").read_text(encoding="utf-8")
    assert 'data-testid="kc-tag-chip"' in page and "setTagFilter(t)" in page
    assert "/api/knowledge-center/sync/status" in page and 'role="progressbar"' in page
    assert "استفاده‌شده" in page
    # no blocking alert() in the sync path
    sync_fn = page[page.index("const syncFromRepos"):page.index("const bootstrapFolders")]
    assert "alert(" not in sync_fn
