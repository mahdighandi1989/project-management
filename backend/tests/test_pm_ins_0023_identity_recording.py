"""PM-INS-0023 — the model's identity is a fact the server states; one event = one chat line; recording without a picker."""

import inspect
from pathlib import Path

from app.api.routes import inspector_recording as IR
from app.api.routes import render_logs as RL
from app.services import model_identity as MI


def test_identity_questions_are_recognised_and_long_requests_are_not():
    assert MI.is_identity_question("دقیقاً با چه مدلی و از چه مسیری جواب می‌دهی؟")
    assert MI.is_identity_question("which model are you?")
    assert not MI.is_identity_question("این باگ رو درست کن")
    assert not MI.is_identity_question("کدوم مدل برای اسکن بهتره؟ " + "x" * 200)


def test_identity_note_states_model_provider_and_route():
    d = MI.identity_note("deepseek-chat")
    assert "deepseek-chat" in d and "DeepSeek" in d and "کلیدِ API" in d and "فقط همین را بگو" in d
    c = MI.identity_note("cloud_code:claude-haiku-4-5-20251001")
    assert "claude-haiku-4-5-20251001" in c and "اشتراکِ Claude" in c and "نه کلیدِ API" in c
    assert "Google" in MI.identity_note("gemini-2.5-flash")


def test_wired_into_the_inspector_chat():
    src = Path(RL.__file__).read_text(encoding="utf-8")
    assert "is_identity_question(request.message)" in src           # light prompt, no repo context
    assert "general_instructions_text = _idn(primary_model)" in src  # every prompt carries the fact
    assert "مدلِ جایگزینِ" in src                                     # a fallback answer names the real model


def test_dedup_window_covers_a_queued_websocket_copy():
    page = Path(__file__).resolve().parents[2] / "frontend/src/app/projects/[id]/page.tsx"
    assert "const INSPECTOR_DEDUP_WINDOW_MS = 60000;" in page.read_text(encoding="utf-8")


def test_server_recording_resolves_the_real_project_address():
    src = inspect.getsource(IR.start_playwright_screencast)
    assert "resolve_preview_frontend_url" in src and "PREVIEW_PATH_MARK" in src
    panel = Path(__file__).resolve().parents[2] / "frontend/src/components/InspectorRecordingPanel.tsx"
    t = panel.read_text(encoding="utf-8")
    assert "ضبطِ سمتِ سرور" in t and "start-screencast" in t and "audio_mic: serverRec ? false" in t
