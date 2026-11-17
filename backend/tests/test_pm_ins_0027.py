"""PM-INS-0027: «فایل X را بساز و این خط را بنویس» goes straight to a plain action_plan — never a deep scan."""

import inspect

from app.services.inspector_intent_resolver import _is_simple_file_op

COORD = ("در فایلِ docs/COORDINATOR_TEST.md (اگر نیست بساز) دقیقاً این یک خط را بنویس و هیچ فایلِ دیگری را تغییر نده: "
         "«آزمونِ هماهنگ‌کننده» سپس اعمال کن (شاخهٔ جدا + PR، بدونِ ادغام)")


def test_the_coordinators_request_is_a_simple_file_op():
    assert _is_simple_file_op(COORD)
    assert _is_simple_file_op("write one line to docs/NOTE.md")
    assert _is_simple_file_op("در README.md این خط را بنویس: سلام")
    assert not _is_simple_file_op("امنیت پروژه را بررسی کن")
    assert not _is_simple_file_op("این صفحه باگ دارد")


def test_smart_chat_decides_on_the_users_own_words_not_the_structured_prompt():
    from app.api.routes import render_logs as R
    src = inspect.getsource(R)
    i = src.index('_orig_msg = (getattr(request, "original_message", None) or "").strip()')
    j = src.index("intent = resolve_intent_from_chat_context(", i)
    block = src[i:j]
    assert "_simple_op(_orig_msg or request.message)" in block and "raise _SkipIntentPath()" in block
    assert "original_message" in R.SmartChatRequest.model_fields
