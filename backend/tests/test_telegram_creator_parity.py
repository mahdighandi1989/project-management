"""🎯 Telegram bot creator-engine parity with the /creator web page.

User asked: "لطفا دقیق ببین این موارد که تغییر و اضافه و اصلاح کردی
در قسمت موتور خالق، با قابلیتش در تلگرام همخوانی داره و همگام سازی
شده یا نه .. چون از اون جا هم می‌شد از طریق موتور خالق پروژه ساخت"

Audit found 6 parity gaps between Telegram and the web Creator
Engine after the recent additions (fullstack, audit, apply-fixes,
model attribution). This file pins all 6 fixes at the source level
so a future refactor can't quietly drop Telegram parity again.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_NOTIF_FILE = (
    Path(__file__).resolve().parents[1]
    / "app/services/notification_service.py"
)


def _read_notif() -> str:
    return _NOTIF_FILE.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Gap 1 + 6: model_ids closure + attribution-aware ai_generate_with_meta
# ─────────────────────────────────────────────────────────────────────────────


def test_telegram_simple_flow_uses_ai_generate_with_meta():
    """The "simple" Telegram creator flow used to pass bare `ai_generate`
    as the AI callable. That returns a plain string, so simple_creator's
    _tracked_ai_generate had nothing to unpack → generated_by stayed
    empty. Fix: use ai_generate_with_meta + wrap in a closure that
    captures model_ids."""
    src = _read_notif()
    idx = src.find("async def _execute_creator_flow")
    assert idx != -1, "_execute_creator_flow function must exist"
    body = src[idx:idx + 6000]
    # Must import the attribution-aware variant (not just plain ai_generate)
    assert "ai_generate_with_meta" in body, (
        "the simple flow must use ai_generate_with_meta so per-file "
        "model attribution flows into ProjectFile.generated_by"
    )
    # Must wrap in a closure (not pass the bare function) so model_ids
    # is captured
    assert "async def _ai_gen" in body or "async def _gen" in body, (
        "ai_generate must be wrapped in a closure that captures the "
        "user's model_ids — otherwise selection is ignored"
    )


def test_telegram_full_flow_uses_ai_generate_with_meta():
    """The "full" (structured-idea) Telegram flow already captured
    model_ids in a closure, but used plain ai_generate (string only).
    The fix switched it to ai_generate_with_meta for attribution."""
    src = _read_notif()
    # Find the second occurrence — full flow comes after simple flow
    idx = src.find("structured.get(\"full_prompt_text\")")
    assert idx != -1, "full structured-prompt flow must exist"
    # Look backwards a bit for the surrounding imports/closure
    pre = src[max(0, idx - 1500):idx]
    assert "ai_generate_with_meta" in pre, (
        "the full flow must also use ai_generate_with_meta — otherwise "
        "structured projects lose attribution even though they honor "
        "model_ids"
    )


def test_telegram_simple_flow_extracts_model_ids_from_creator_data():
    """Both flows now pull model_ids from creator_data (the same dict
    where the model picker stores its choice). Without this, Telegram
    file generation ignored the user's model selection on the simple
    flow."""
    src = _read_notif()
    idx = src.find("async def _execute_creator_flow")
    body = src[idx:idx + 2000]
    assert 'data.get("model_ids"' in body or "model_ids" in body, (
        "_execute_creator_flow must extract model_ids from creator_data "
        "so the user's selection on the Telegram model picker is honored"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gap 2: auto-detect fallback (was "fastapi", must now be "fullstack")
# ─────────────────────────────────────────────────────────────────────────────


def test_telegram_auto_detect_failure_falls_back_to_fullstack():
    """The /creator web page changed its auto-detect failure fallback
    from "python" → "fullstack" (because most projects users build are
    web apps that need both halves). Telegram still used "fastapi" →
    user got backend-only on detect failure even when they wanted a
    dashboard. The fix aligns Telegram with the web fallback."""
    src = _read_notif()
    idx = src.find("async def _execute_creator_flow")
    body = src[idx:idx + 4000]
    # The old fallback must be gone
    assert 'fallback to fastapi' not in body, (
        "Telegram must NOT fall back to fastapi on auto-detect failure "
        "— that gives backend-only scaffolding for users who picked auto"
    )
    # The new fallback must be in
    assert 'fallback to fullstack' in body or '"fullstack"' in body, (
        "auto-detect failure path must default to fullstack (matching "
        "the web Creator Engine)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gap 3: detect_project_type must receive model_ids
# ─────────────────────────────────────────────────────────────────────────────


def test_telegram_detect_project_type_receives_model_ids():
    """The detect endpoint accepts model_ids but Telegram was calling
    it without — wasted tokens, ignored user selection. Fix: pass
    model_ids through."""
    src = _read_notif()
    idx = src.find("async def _execute_creator_flow")
    body = src[idx:idx + 3000]
    # find the _detect_project_type call
    det_idx = body.find("_detect_project_type(")
    assert det_idx != -1, "_detect_project_type call must exist"
    # Slice to closing paren + a bit
    call_body = body[det_idx:det_idx + 800]
    assert "model_ids" in call_body, (
        "_detect_project_type must be called with model_ids so the "
        "user's selected models are used for detection too"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gap 4: type picker must include "fullstack" option
# ─────────────────────────────────────────────────────────────────────────────


def test_telegram_type_picker_includes_fullstack():
    """The hardcoded type-picker list must include fullstack so users
    don't have to rely on auto-detect to get both halves."""
    src = _read_notif()
    # Search for the type-picker definition (the list of (label, value))
    assert '"fullstack"' in src, (
        "Telegram type picker must include 'fullstack' as a manual "
        "option for parity with the web Creator Engine"
    )
    # And it must be one of the rows in the picker, not just somewhere
    # else in the file. Look for the patterns specific to the picker.
    assert '"🌐 fullstack"' in src or '"🌐 Fullstack"' in src or "fullstack\", \"fullstack" in src, (
        "fullstack must be a labeled button in the type picker, not "
        "just incidentally in the file"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gap 5: audit + apply-fixes commands in Telegram
# ─────────────────────────────────────────────────────────────────────────────


def test_telegram_project_list_has_audit_button():
    """Every project entry in the Telegram "my projects" list must
    show the audit + apply-fixes buttons — otherwise the user has to
    leave Telegram to do anything after creation."""
    src = _read_notif()
    idx = src.find("async def _list_my_creator_projects")
    assert idx != -1
    body = src[idx:idx + 4000]
    assert "creator_audit:" in body, (
        "Telegram project list must have a 🔎 audit button so the user "
        "can re-review without leaving the bot"
    )
    assert "creator_apply_fixes:" in body, (
        "Telegram project list must have an ✨ apply-fixes button"
    )


def test_telegram_has_audit_callback_handler():
    """The button is useless without a callback handler. The handler
    must route to the same audit_project endpoint the web UI uses, so
    backend logic stays in one place (parity-by-construction)."""
    src = _read_notif()
    assert 'data.startswith("creator_audit:")' in src, (
        "callback handler for creator_audit: must exist — without it "
        "the button does nothing"
    )
    # Must call the actual backend endpoint (no Telegram-specific
    # parallel implementation)
    assert "audit_project" in src and "AuditProjectRequest" in src, (
        "Telegram audit must route through the same audit_project "
        "endpoint as the web UI — no parallel implementation"
    )


def test_telegram_has_apply_fixes_callback_handler():
    """Same for apply-fixes: handler must route to apply_audit_fixes
    so backend logic isn't forked."""
    src = _read_notif()
    assert 'data.startswith("creator_apply_fixes:")' in src
    assert "apply_audit_fixes" in src and "ApplyAuditFixesRequest" in src


def test_telegram_audit_handler_honors_user_model_selection():
    """The handler must pull model_ids from creator_data so the audit
    on Telegram uses the same models the user picked at create time.
    Without this, audit would use 'all active' (the very bug we
    fixed for the web UI in an earlier commit)."""
    src = _read_notif()
    idx = src.find('data.startswith("creator_audit:")')
    assert idx != -1
    body = src[idx:idx + 3000]
    assert "model_ids" in body, (
        "audit handler must extract model_ids from creator_data so "
        "user's Telegram-time selection is honored"
    )


def test_telegram_apply_fixes_handler_handles_promote_decision():
    """For Telegram parity, the recommended action is "promote if
    needed + add missing + modify selected". Since Telegram has no
    per-item checkbox UI for the delete category, delete is left as
    an explicit web action (safer default). The handler must check
    the project's current type before promoting."""
    src = _read_notif()
    idx = src.find('data.startswith("creator_apply_fixes:")')
    body = src[idx:idx + 3000]
    # Handler must check project.project_type to decide promotion
    assert "project_type" in body and "fullstack" in body, (
        "apply-fixes handler must check project_type so it only "
        "promotes when not already fullstack"
    )
