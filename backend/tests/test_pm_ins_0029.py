"""PM-INS-0029: a question gets a direct answer (never a deep scan); experiences reach the creator and the scan."""

import inspect

from app.services.inspector_quick_classify import is_answer_only

Q = ("Playwright در محیطِ ابری پشتِ پراکسی کار نمی‌کند و خطای ERR_CERT_AUTHORITY_INVALID می‌دهد؛ "
     "کوتاه بگو چه کنم؟ (فقط پاسخ، تغییر فایل نه)")


def test_the_coordinators_question_is_answer_only():
    assert is_answer_only(Q)
    assert is_answer_only("Playwright پشت پراکسی ERR_CERT_AUTHORITY_INVALID می‌دهد، چه کنم؟")
    assert is_answer_only("how do I fix CORS behind nginx?")
    # change requests and plain tasks are not
    assert not is_answer_only("این باگ را درست کن چطور؟")
    assert not is_answer_only("امنیت پروژه را بررسی کن")
    assert not is_answer_only("در فایل docs/X.md این خط را بنویس")


def test_smart_chat_never_scans_for_a_question_and_says_why():
    from app.api.routes import render_logs as R
    src = inspect.getsource(R)
    i = src.index("# (PM-INS-0029) a question that wants only an answer never starts a deep scan")
    assert "_answer_only(_orig_msg or request.message)" in src[i:i + 400] and "raise _SkipIntentPath()" in src[i:i + 400]
    j = src.index("# (PM-INS-0029) a scan with NO path and NO section for a question")
    assert "intent.custom_paths or intent.selected_sections" in src[j:j + 500]
    assert "'step': 'no_scan'" in src  # the reason is the first line in the chat
    k = src.index("_quick_question = (not request.reply_to) and (")
    assert "_ao(request.message)" in src[k:k + 300]  # and it is answered as a QUESTION (no action_plan)


def test_quick_override_keeps_the_users_own_question():
    from app.api.routes.render_logs import SmartChatRequest, _apply_quick_question_override
    r = SmartChatRequest(project_id="p", model_ids=["deepseek-chat"], message="# پرامپتِ ساختارمند\n…بلند…",
                         original_message=Q)
    assert _apply_quick_question_override(r) and r.message == Q


def test_creator_and_oversight_scan_read_experiences():
    from app.services import creator_idea_to_prompt as C, oversight_service as O
    c = inspect.getsource(C.idea_to_strong_prompt_for_creator)
    assert 'experience_context as _kc_ctx' in c and '"creator"' in c and '"experiences_used"' in c
    o = inspect.getsource(O.OversightService.scan_project)
    assert 'experience_context as _kc_ctx' in o and '"oversight_scan"' in o
