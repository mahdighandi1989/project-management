"""Stage 2 — AC enricher tests (با mock کردن AI).

تست‌ها AI واقعی را call نمی‌کنند؛ به جای آن `get_ai_manager` را mock می‌کنیم.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# pre-import ai_manager so that patch() can resolve the module path
import app.services.ai_manager  # noqa: F401

from app.services.verify_runtime.ac_enricher import (
    _parse_ai_response,
    _ac_already_classified,
    enrich_acs_with_verify_plans,
)


class TestParseAiResponse:
    def test_valid_json(self):
        raw = '{"acs": [{"index": 0, "verify_method": "ui_interaction", "verify_plan": {"base": "frontend", "ui_steps": []}}]}'
        r = _parse_ai_response(raw)
        assert 0 in r
        assert r[0]["verify_method"] == "ui_interaction"
        assert r[0]["verify_plan"]["base"] == "frontend"

    def test_json_with_surrounding_text(self):
        raw = 'Here is the JSON:\n{"acs": [{"index": 0, "verify_method": "static"}]}\nThanks.'
        r = _parse_ai_response(raw)
        assert r[0]["verify_method"] == "static"

    def test_invalid_method_falls_back(self):
        raw = '{"acs": [{"index": 0, "verify_method": "not_a_thing"}]}'
        r = _parse_ai_response(raw)
        assert r[0]["verify_method"] == "static"

    def test_empty_string(self):
        assert _parse_ai_response("") == {}

    def test_malformed_json(self):
        assert _parse_ai_response("not json at all") == {}

    def test_missing_acs_key(self):
        assert _parse_ai_response('{"other": "data"}') == {}

    def test_non_int_index_skipped(self):
        raw = '{"acs": [{"index": "abc", "verify_method": "static"}, {"index": 1, "verify_method": "api_response"}]}'
        r = _parse_ai_response(raw)
        assert 1 in r
        assert "abc" not in r


class TestAlreadyClassified:
    def test_default_static_not_classified(self):
        ac = {"text": "x", "verify_method": "static", "verify_plan": {"grep_patterns": [], "files_hint": []}}
        assert not _ac_already_classified(ac)

    def test_non_static_method_is_classified(self):
        ac = {"text": "x", "verify_method": "ui_interaction", "verify_plan": {}}
        assert _ac_already_classified(ac)

    def test_static_with_real_patterns_is_classified(self):
        ac = {"text": "x", "verify_method": "static", "verify_plan": {"grep_patterns": ["foo"], "files_hint": []}}
        assert _ac_already_classified(ac)


class TestEnrichWithAiMock:
    @pytest.mark.asyncio
    async def test_enrich_empty_list(self):
        r = await enrich_acs_with_verify_plans([])
        assert r == []

    @pytest.mark.asyncio
    async def test_already_classified_skipped(self):
        """اگر همه AC قبلاً classified شده‌اند، AI اصلاً call نمی‌شود."""
        acs = [{
            "text": "X",
            "verify_method": "ui_interaction",
            "verify_plan": {"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}]},
        }]
        with patch("app.services.ai_manager.get_ai_manager") as mock_mgr:
            r = await enrich_acs_with_verify_plans(acs)
            mock_mgr.assert_not_called()
        assert r[0]["verify_method"] == "ui_interaction"

    @pytest.mark.asyncio
    async def test_enrich_with_mocked_ai(self):
        """با AI mock، AC های static به ui_interaction تبدیل می‌شوند."""
        fake_response = MagicMock()
        fake_response.content = (
            '{"acs": [{"index": 0, "verify_method": "ui_interaction", '
            '"verify_plan": {"base": "frontend", "ui_steps": ['
            '{"action": "navigate", "url": "/login"}]}}]}'
        )
        fake_mgr = MagicMock()
        fake_mgr.generate = AsyncMock(return_value=fake_response)

        with patch("app.services.ai_manager.get_ai_manager", return_value=fake_mgr):
            r = await enrich_acs_with_verify_plans(
                ["وقتی روی login کلیک می‌کنم، صفحه باز شود"],
                model_id="test-model",
            )
        assert r[0]["verify_method"] == "ui_interaction"
        assert r[0]["verify_plan"]["ui_steps"][0]["url"] == "/login"

    @pytest.mark.asyncio
    async def test_ai_failure_graceful_degrade(self):
        """اگر AI exception داد، AC ها با method=static باقی می‌مانند."""
        fake_mgr = MagicMock()
        fake_mgr.generate = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.services.ai_manager.get_ai_manager", return_value=fake_mgr):
            r = await enrich_acs_with_verify_plans(
                ["AC ساده", "AC دیگر"],
                model_id="test-model",
            )
        assert len(r) == 2
        assert all(ac["verify_method"] == "static" for ac in r)

    @pytest.mark.asyncio
    async def test_ai_returns_malformed_json(self):
        """AI پاسخ غیر-JSON داد → AC ها با static."""
        fake_response = MagicMock()
        fake_response.content = "I cannot help with that."
        fake_mgr = MagicMock()
        fake_mgr.generate = AsyncMock(return_value=fake_response)

        with patch("app.services.ai_manager.get_ai_manager", return_value=fake_mgr):
            r = await enrich_acs_with_verify_plans(
                ["test ac"],
                model_id="test-model",
            )
        assert r[0]["verify_method"] == "static"

    @pytest.mark.asyncio
    async def test_no_model_id_skips_ai(self, monkeypatch):
        """اگر model_id نباشد و registry هم default ندهد → skip."""
        import app.core.models_registry as reg
        monkeypatch.setattr(reg, "DEFAULT_EXTRACTION_MODEL_ID", "")
        with patch("app.services.ai_manager.get_ai_manager") as mock_mgr:
            r = await enrich_acs_with_verify_plans(["x"], model_id=None)
            mock_mgr.assert_not_called()
        assert r[0]["verify_method"] == "static"
