"""Tests for render_autodetect — مappping repo → Render URLs."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.verify_runtime.render_autodetect import (
    _normalize_repo_url,
    _service_repo_full_name,
    _service_url,
    _service_type,
    detect_render_urls_for_repo,
    detect_repo_url,
)


class TestNormalizeRepoUrl:
    def test_https_url(self):
        assert _normalize_repo_url("https://github.com/Foo/Bar") == "foo/bar"

    def test_with_git_suffix(self):
        assert _normalize_repo_url("https://github.com/foo/bar.git") == "foo/bar"

    def test_ssh_url(self):
        assert _normalize_repo_url("git@github.com:foo/bar.git") == "foo/bar"

    def test_already_owner_repo(self):
        assert _normalize_repo_url("foo/bar") == "foo/bar"

    def test_empty(self):
        assert _normalize_repo_url("") == ""


class TestServiceFieldExtractors:
    def test_repo_extraction_from_flat(self):
        svc = {"repo": "https://github.com/Foo/Bar.git", "type": "web_service"}
        assert _service_repo_full_name(svc) == "foo/bar"

    def test_repo_extraction_from_nested(self):
        svc = {"service": {"repo": "https://github.com/X/Y"}}
        assert _service_repo_full_name(svc) == "x/y"

    def test_url_from_serviceDetails(self):
        svc = {"serviceDetails": {"url": "https://example.onrender.com"}}
        assert _service_url(svc) == "https://example.onrender.com"

    def test_url_flat(self):
        svc = {"url": "https://example.onrender.com/"}
        assert _service_url(svc) == "https://example.onrender.com"

    def test_type(self):
        assert _service_type({"type": "static_site"}) == "static_site"
        assert _service_type({"type": "web_service"}) == "web_service"


class TestDetectRepoUrl:
    def test_basic(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        assert detect_repo_url("a/b") == "https://github.com/a/b.git"

    def test_with_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_abc")
        assert detect_repo_url("a/b") == "https://ghp_abc@github.com/a/b.git"

    def test_invalid(self):
        assert detect_repo_url("") == ""
        assert detect_repo_url("noslash") == ""


class TestDetectRenderUrlsForRepo:
    @pytest.mark.asyncio
    async def test_no_render_token_returns_empty(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        r = await detect_render_urls_for_repo("foo/bar")
        assert r["source"] == "not_configured"
        assert r["frontend_base_url"] is None
        assert r["backend_base_url"] is None

    @pytest.mark.asyncio
    async def test_matches_static_site_as_frontend(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "rnd_test")
        services = [
            {
                "service": {
                    "name": "my-frontend",
                    "type": "static_site",
                    "repo": "https://github.com/foo/bar.git",
                    "serviceDetails": {"url": "https://my-frontend.onrender.com"},
                }
            }
        ]
        fake_client = MagicMock()
        fake_client.list_services = AsyncMock(return_value=services)
        fake_client.close = AsyncMock()
        with patch("app.services.deploy_service.RenderDeployService", return_value=fake_client):
            r = await detect_render_urls_for_repo("foo/bar")
        assert r["source"] == "render_api"
        assert r["frontend_base_url"] == "https://my-frontend.onrender.com"
        assert r["backend_base_url"] is None
        assert len(r["matched_services"]) == 1

    @pytest.mark.asyncio
    async def test_matches_web_service_as_backend(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "rnd_test")
        services = [
            {
                "service": {
                    "name": "my-api",
                    "type": "web_service",
                    "repo": "https://github.com/foo/bar.git",
                    "serviceDetails": {"url": "https://my-api.onrender.com"},
                }
            }
        ]
        fake_client = MagicMock()
        fake_client.list_services = AsyncMock(return_value=services)
        fake_client.close = AsyncMock()
        with patch("app.services.deploy_service.RenderDeployService", return_value=fake_client):
            r = await detect_render_urls_for_repo("foo/bar")
        assert r["backend_base_url"] == "https://my-api.onrender.com"
        assert r["frontend_base_url"] is None

    @pytest.mark.asyncio
    async def test_web_with_frontend_in_name_classifies_as_frontend(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "rnd_test")
        services = [
            {
                "service": {
                    "name": "ai-creator-frontend",  # has "frontend" in name
                    "type": "web_service",
                    "repo": "https://github.com/foo/bar.git",
                    "serviceDetails": {"url": "https://ai-creator-frontend.onrender.com"},
                }
            },
            {
                "service": {
                    "name": "ai-creator-backend",
                    "type": "web_service",
                    "repo": "https://github.com/foo/bar.git",
                    "serviceDetails": {"url": "https://ai-creator-backend.onrender.com"},
                }
            },
        ]
        fake_client = MagicMock()
        fake_client.list_services = AsyncMock(return_value=services)
        fake_client.close = AsyncMock()
        with patch("app.services.deploy_service.RenderDeployService", return_value=fake_client):
            r = await detect_render_urls_for_repo("foo/bar")
        assert r["frontend_base_url"] == "https://ai-creator-frontend.onrender.com"
        assert r["backend_base_url"] == "https://ai-creator-backend.onrender.com"

    @pytest.mark.asyncio
    async def test_unrelated_repo_no_match(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "rnd_test")
        services = [
            {
                "service": {
                    "name": "other",
                    "type": "web_service",
                    "repo": "https://github.com/other/proj.git",
                    "serviceDetails": {"url": "https://other.onrender.com"},
                }
            }
        ]
        fake_client = MagicMock()
        fake_client.list_services = AsyncMock(return_value=services)
        fake_client.close = AsyncMock()
        with patch("app.services.deploy_service.RenderDeployService", return_value=fake_client):
            r = await detect_render_urls_for_repo("foo/bar")
        assert r["frontend_base_url"] is None
        assert r["backend_base_url"] is None
        assert r["matched_services"] == []

    @pytest.mark.asyncio
    async def test_api_error_returns_error_source(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "rnd_test")
        fake_client = MagicMock()
        fake_client.list_services = AsyncMock(side_effect=RuntimeError("boom"))
        fake_client.close = AsyncMock()
        with patch("app.services.deploy_service.RenderDeployService", return_value=fake_client):
            r = await detect_render_urls_for_repo("foo/bar")
        assert r["source"] == "error"
        assert "boom" in r.get("error", "")

    @pytest.mark.asyncio
    async def test_invalid_repo_name(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "rnd_test")
        r = await detect_render_urls_for_repo("")
        assert r["source"] == "error"
