# -*- coding: utf-8 -*-
"""تست‌های قابلیت ضبط ویدئوی صفحه (Screen Recording) برای «بازرس ویژه».

پوشش:
- مدل ScreenRecording.to_dict و round-trip فیلدهای JSON
- build_inspector_strong_prompt: درج بخش transcript صوت + مسیر تعامل کاربر
- FromInspectorRequest: پذیرش mode='video_record' و فیلدهای recording
- audio_transcription_service: resolve مدل پیش‌فرض از env

هیچ‌کدام به DB یا فراخوانی واقعی AI نیاز ندارند.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# scenario_1 — مدل ScreenRecording.to_dict
# ---------------------------------------------------------------------------


def test_scenario_1_model_to_dict_json_roundtrip():
    from app.models.screen_recording import ScreenRecording

    rec = ScreenRecording()
    rec.id = 5
    rec.project_id = "proj-1"
    rec.inspector_session_id = "sess-9"
    rec.video_file_id = "vid-abc"
    rec.audio_source = "both"
    rec.handsfree = "true"
    rec.duration_ms = 12345
    rec.transcript = "این یک تست است"
    rec.console_logs = json.dumps([{"level": "error", "message": "boom"}])
    rec.user_interactions = json.dumps([{"type": "click", "target": "button#go"}])
    rec.status = "transcribed"

    d = rec.to_dict()
    assert d["id"] == 5
    assert d["project_id"] == "proj-1"
    assert d["audio_source"] == "both"
    # handsfree متن "true" باید به bool واقعی تبدیل شود
    assert d["handsfree"] is True
    assert d["duration_ms"] == 12345
    assert d["transcript"] == "این یک تست است"
    assert d["console_logs"][0]["message"] == "boom"
    assert d["user_interactions"][0]["target"] == "button#go"
    assert d["status"] == "transcribed"


def test_scenario_2_model_loads_handles_empty_and_bad_json():
    from app.models.screen_recording import ScreenRecording

    rec = ScreenRecording()
    assert rec._loads(None) == []
    assert rec._loads("") == []
    assert rec._loads("not-json") == []
    assert rec._loads('{"a":1}') == []  # dict نه list → []
    assert rec._loads('[{"x":1}]') == [{"x": 1}]


# ---------------------------------------------------------------------------
# scenario_3 — strong prompt شامل transcript و تعاملات
# ---------------------------------------------------------------------------


def test_scenario_3_strong_prompt_includes_transcript_and_interactions():
    from app.services.oversight_inspector_bridge import build_inspector_strong_prompt

    transcript = "میخوام دکمهٔ ذخیره وقتی روش کلیک میکنم سبز بشه"
    interactions = [
        {"type": "click", "target": "button#save", "label": "ذخیره",
         "page_url": "/settings", "timestamp": "2026-06-02T10:00:00Z"},
        {"type": "navigate", "page_url": "/dashboard",
         "timestamp": "2026-06-02T10:00:05Z"},
    ]

    prompt = build_inspector_strong_prompt(
        user_request="بهبود دکمهٔ ذخیره",
        mode="video_record",
        audio_transcript=transcript,
        user_interactions=interactions,
        recording_duration_ms=8000,
    )

    # transcript عیناً (بدون خلاصه) باید موجود باشد
    assert "🎙 توضیحات صوتی کاربر" in prompt
    assert transcript in prompt
    # مسیر تعامل کاربر
    assert "🖱 مسیر تعامل کاربر" in prompt
    assert "button#save" in prompt


def test_scenario_4_strong_prompt_omits_recording_sections_when_absent():
    from app.services.oversight_inspector_bridge import build_inspector_strong_prompt

    prompt = build_inspector_strong_prompt(
        user_request="یک تغییر ساده",
        mode="chat",
    )
    assert "🎙 توضیحات صوتی کاربر" not in prompt
    assert "🖱 مسیر تعامل کاربر" not in prompt


# ---------------------------------------------------------------------------
# scenario_5 — FromInspectorRequest فیلدهای recording
# ---------------------------------------------------------------------------


def test_scenario_5_from_inspector_request_accepts_video_record():
    from app.api.routes.oversight import FromInspectorRequest

    req = FromInspectorRequest(
        project_id="p1",
        mode="video_record",
        user_request="",
        audio_transcript="صدای ضبط‌شده",
        user_interactions=[{"type": "click", "target": "a#x"}],
        recording_id=42,
        recording_video_file_id="vid-1",
        recording_duration_ms=5000,
    )
    assert req.mode == "video_record"
    assert req.recording_id == 42
    assert req.audio_transcript == "صدای ضبط‌شده"
    assert req.user_interactions[0]["target"] == "a#x"

    # backward compat: بدون فیلدهای recording
    req2 = FromInspectorRequest(project_id="p1", mode="chat", user_request="hi")
    assert req2.recording_id is None
    assert req2.audio_transcript is None


# ---------------------------------------------------------------------------
# scenario_6 — resolve مدل پیش‌فرض transcription از env
# ---------------------------------------------------------------------------


def test_scenario_6_audio_default_model(monkeypatch):
    import app.services.audio_transcription_service as ats

    monkeypatch.delenv("AUDIO_TRANSCRIPTION_MODEL", raising=False)
    assert ats._default_model_id() == "gemini-2.5-flash"

    monkeypatch.setenv("AUDIO_TRANSCRIPTION_MODEL", "custom-model-x")
    assert ats._default_model_id() == "custom-model-x"


if __name__ == "__main__":
    import types

    class _MP:
        """monkeypatch مینیمال برای اجرای inline بدون pytest."""
        def __init__(self):
            self._env = {}

        def setenv(self, k, v):
            import os
            self._env[k] = os.environ.get(k)
            os.environ[k] = v

        def delenv(self, k, raising=False):
            import os
            self._env[k] = os.environ.get(k)
            os.environ.pop(k, None)

        def undo(self):
            import os
            for k, v in self._env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    tests = [
        test_scenario_1_model_to_dict_json_roundtrip,
        test_scenario_2_model_loads_handles_empty_and_bad_json,
        test_scenario_3_strong_prompt_includes_transcript_and_interactions,
        test_scenario_4_strong_prompt_omits_recording_sections_when_absent,
        test_scenario_5_from_inspector_request_accepts_video_record,
        test_scenario_6_audio_default_model,
    ]
    passed = failed = 0
    for t in tests:
        name = t.__name__
        mp = _MP()
        try:
            if "monkeypatch" in t.__code__.co_varnames:
                t(mp)
            else:
                t()
            print(f"OK  {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL {name} — {type(e).__name__}: {e}")
            failed += 1
        finally:
            mp.undo()
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
